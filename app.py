from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


from pathlib import Path
import math
import os
import time
import secrets
import hashlib
from contextlib import closing
from urllib.parse import urlsplit
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

# ADDED: Check the basic format of email addresses.
import re

# ADDED: Handle database errors, including duplicate email addresses.
import sqlite3

# Verify hashes from accounts created by the previous signup endpoint.
from werkzeug.security import check_password_hash

# ADDED: Use the SQLite connection function from database.py.
from database import get_connection, initialize_database

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory, g, redirect

# Locate your website and trained model.
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
MODEL_PATH = BASE_DIR / "model" / "stress_knn_bundle.joblib"

# Load the trained pipeline and its input information.
bundle = joblib.load(MODEL_PATH)

model = bundle["pipeline"]
all_features = bundle["features"]
selected_features = bundle["selected_features"]

# Serve website files from the web folder.
app = Flask(
    __name__,
    static_folder=str(WEB_DIR),
    static_url_path="",
)

# Limit request bodies to 4 KB (4,096 bytes).
# This rejects oversized submissions before processing the answers.
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024
app.config.update(
    SESSION_COOKIE_NAME="pahuway_session",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
    AUTH_SESSION_SECONDS=int(os.environ.get("AUTH_SESSION_SECONDS", "28800")),
)
initialize_database()
password_hasher = PasswordHasher()
dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))
limiter = Limiter(key_func=get_remote_address, app=app,
                  storage_uri="memory://", headers_enabled=True)


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


@app.before_request
def authenticate_request():
    g.user = None
    g.auth_session = None
    token = request.cookies.get(app.config["SESSION_COOKIE_NAME"], "")
    if token and len(token) <= 128:
        with closing(get_connection()) as connection:
            row = connection.execute(
                """SELECT s.*, u.display_name, u.email FROM auth_sessions s
                   JOIN users u ON u.id = s.user_id
                   WHERE token_hash = ? AND expires_at > ?""",
                (token_digest(token), int(time.time())),
            ).fetchone()
        if row:
            g.auth_session = row
            g.user = {"id": row["user_id"], "display_name": row["display_name"],
                      "email": row["email"]}
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.path.startswith("/api/"):
        origin = request.headers.get("Origin")
        expected = urlsplit(os.environ.get("APP_ORIGIN", request.host_url))
        if (request.headers.get("Sec-Fetch-Site") == "cross-site" or
                (origin and urlsplit(origin)[:2] != expected[:2])):
            return jsonify(error="Request origin is not allowed."), 403
        if not request.is_json:
            return jsonify(error="Send data as JSON."), 415
        if g.user and not secrets.compare_digest(
            request.headers.get("X-CSRF-Token", "").encode(), g.auth_session["csrf_token"].encode()
        ):
            return jsonify(error="Session verification failed. Refresh and try again."), 403


@app.after_request
def security_headers(response):
    if request.path.startswith("/api/") or response.mimetype == "text/html":
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/dashboard")
def dashboard():
    if not g.user:
        return redirect("/sign-in.html")
    return send_from_directory(WEB_DIR, "results.html")


@app.get("/api/session")
def current_session():
    if not g.user:
        return jsonify(error="Please sign in."), 401
    return jsonify(user=g.user, csrf_token=g.auth_session["csrf_token"],
                   expires_at=g.auth_session["expires_at"])


@app.post("/api/login")
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True)
    if (not isinstance(data, dict) or set(data) != {"email", "password"}
            or not all(isinstance(v, str) for v in data.values())
            or not data["email"].strip() or not data["password"]
            or len(data["email"]) > 254 or len(data["password"]) > 128):
        return jsonify(error="Provide your email and password."), 400
    with closing(get_connection()) as connection:
        user = connection.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE",
                                  (data["email"].strip().lower(),)).fetchone()
        stored = user["password_hash"] if user else dummy_hash
        valid = False
        try:
            if stored.startswith("$argon2"):
                valid = password_hasher.verify(stored, data["password"])
            elif stored.startswith(("scrypt:", "pbkdf2:")):
                valid = check_password_hash(stored, data["password"])
        except (VerificationError, InvalidHashError, ValueError):
            pass
        if not user or not valid:
            return jsonify(error="Incorrect email or password."), 401
        if not stored.startswith("$argon2id$") or password_hasher.check_needs_rehash(stored):
            connection.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                               (password_hasher.hash(data["password"]), user["id"]))
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        expires = int(time.time()) + app.config["AUTH_SESSION_SECONDS"]
        connection.execute("DELETE FROM auth_sessions WHERE expires_at <= ? OR token_hash = ?",
                           (int(time.time()), token_digest(request.cookies.get(app.config["SESSION_COOKIE_NAME"], ""))))
        connection.execute("INSERT INTO auth_sessions(token_hash, user_id, csrf_token, expires_at) VALUES (?, ?, ?, ?)",
                           (token_digest(token), user["id"], csrf, expires))
        connection.commit()
    response = jsonify(message="Signed in successfully.", redirect="/dashboard")
    response.set_cookie(app.config["SESSION_COOKIE_NAME"], token,
                        max_age=app.config["AUTH_SESSION_SECONDS"], httponly=True,
                        secure=app.config["SESSION_COOKIE_SECURE"], samesite="Lax", path="/")
    return response


@app.post("/api/logout")
def logout():
    with closing(get_connection()) as connection:
        connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?",
                           (token_digest(request.cookies.get(app.config["SESSION_COOKIE_NAME"], "")),))
        connection.commit()
    response = jsonify(message="Signed out.")
    response.delete_cookie(app.config["SESSION_COOKIE_NAME"], path="/",
                           secure=app.config["SESSION_COOKIE_SECURE"], httponly=True, samesite="Lax")
    return response


@app.get("/api/history")
def history():
    if not g.user:
        return jsonify(error="Please sign in."), 401
    with closing(get_connection()) as connection:
        rows = connection.execute(
            "SELECT id, stress_level, created_at FROM assessments WHERE user_id = ? ORDER BY id DESC LIMIT 50",
            (g.user["id"],),
        ).fetchall()
    return jsonify(results=[dict(row) for row in rows])


@app.get("/")
def home():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ready",
        "required_inputs": selected_features,
    })


@app.post("/api/predict")
# Allow at most 10 prediction requests per minute from each IP address.
# Extra requests receive HTTP 429 to reduce repeated requests and abuse.
@limiter.limit("10 per minute")
def predict():
    answers = request.get_json(silent=True)

    if not isinstance(answers, dict):
        return jsonify({"error": "Send answers as a JSON object."}), 400

    # Reject unexpected field names.
    unknown = set(answers) - set(selected_features)
    if unknown:
        return jsonify({
            "error": f"Unknown inputs: {', '.join(sorted(unknown))}"
        }), 400

    # Create all 11 columns in their original order.
    row = {feature: np.nan for feature in all_features}

    # Require a valid number for each selected feature.
    for feature in selected_features:
        value = answers.get(feature)

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return jsonify({
                "error": f"{feature} must contain a number."
            }), 400

        try:
            value = float(value)
        except (ValueError, OverflowError):
            return jsonify({"error": f"{feature} is invalid."}), 400

        if not math.isfinite(value):
            return jsonify({
                "error": f"{feature} must be a finite number."
            }), 400

        # Supported ranges for the current prototype.
        limits = {
            "Sleep_Hours": (4, 9),
            "Screen_Time": (2, 10),
            "Assignment_Load": (1, 9),
            "Exam_Pressure": (1, 10),
            "Social_Support": (1, 10),
        }

        minimum, maximum = limits[feature]

        if not minimum <= value <= maximum:
            return jsonify({
                "error": (
                    f"{feature} is outside this prototype's supported "
                    f"range of {minimum}–{maximum}."
                )
            }), 400

        # Ratings must be whole numbers; hours can contain decimals.
        rating_fields = {
            "Assignment_Load",
            "Exam_Pressure",
            "Social_Support",
        }

        if feature in rating_fields and not value.is_integer():
            return jsonify({
                "error": f"{feature} must be a whole-number rating."
            }), 400

        row[feature] = value

    input_data = pd.DataFrame([row], columns=all_features)

    try:
        # Apply saved preprocessing and run the trained KNN.
        prediction = model.predict(input_data)[0]

        if g.user:
            with closing(get_connection()) as connection:
                connection.execute(
                    "INSERT INTO assessments(user_id, stress_level) VALUES (?, ?)",
                    (g.user["id"], str(prediction)),
                )
                connection.commit()

        return jsonify({
            "stress_level": str(prediction),
        })

    except Exception:
        app.logger.exception("Prediction failed")
        return jsonify({
            "error": "Unable to calculate a prediction."
        }), 500

# ADDED: Create user accounts from the signup form.
# Limit signup attempts to five per minute per IP address.
@app.post("/api/signup")
@limiter.limit("5 per minute")
def signup():
    # Accept JSON only, matching what our JavaScript form will send.
    if not request.is_json:
        return jsonify({"error": "Send data as JSON."}), 415

    data = request.get_json(silent=True)

    # Reject invalid JSON or values that are not an object.
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid signup data."}), 400

    # Require exactly these three fields.
    # This also rejects unexpected fields supplied by a caller.
    required = {"display_name", "email", "password"}

    if set(data) != required:
        return jsonify({
            "error": "Provide your name, email, and password."
        }), 400

    # Check types before using string operations.
    if not all(isinstance(data[field], str) for field in required):
        return jsonify({
            "error": "All fields must contain text."
        }), 400

    # Remove surrounding spaces from names and email addresses.
    # Use lowercase emails for consistent account lookup.
    display_name = data["display_name"].strip()
    email = data["email"].strip().lower()

    # Preserve the password exactly as entered.
    password = data["password"]

    # Check lengths in the backend, even if the website also checks them.
    if not 1 <= len(display_name) <= 80:
        return jsonify({
            "error": "Your name must contain 1–80 characters."
        }), 400

    # Check basic email formatting.
    # This does not prove that the user owns the email address.
    if (
        len(email) > 254
        or not re.fullmatch(r"[^@\s]+@[^@\s]+[.][^@\s]+", email)
    ):
        return jsonify({
            "error": "Enter a valid email address."
        }), 400

    # Accept long passwords or passphrases without silently shortening them.
    if not 15 <= len(password) <= 128:
        return jsonify({
            "error": "Use a password containing 15–128 characters."
        }), 400

    # Generate a salted password hash.
    # The original password is never saved in the database.
    password_hash = password_hasher.hash(password)

    connection = None

    try:
        connection = get_connection()

        # Parameterized SQL prevents user values from becoming SQL commands.
        # Never replace these placeholders with an f-string.
        connection.execute(
            """
            INSERT INTO users (display_name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (display_name, email, password_hash),
        )

        # Save the new account permanently.
        connection.commit()

        # HTTP 201 means a new record was created.
        # Creating an account does not automatically log the user in.
        return jsonify({
            "message": "Account created successfully."
        }), 201

    except sqlite3.IntegrityError:
        # The UNIQUE email constraint prevents duplicate accounts.
        return jsonify({
            "error": (
                "Unable to create this account. "
                "Try another email or sign in."
            )
        }), 409

    except sqlite3.Error:
        # Log technical details on the server.
        # Show users a general message instead of database details.
        app.logger.exception("Account creation failed")

        return jsonify({
            "error": "Unable to create your account. Please try again later."
        }), 500

    finally:
        # Close the connection whether account creation succeeds or fails.
        if connection is not None:
            connection.close()

            

# CHANGED: This message applies to both assessment and account requests.
# HTTP 413 means the request body exceeds our 4 KB limit.
@app.errorhandler(413)
def request_too_large(error):
    return jsonify({
        "error": "Request too large. Please reduce the submitted data."
    }), 413

# Return a readable JSON message when the request limit is exceeded.
# HTTP 429 means too many requests were sent.
@app.errorhandler(429)
def too_many_requests(error):
    return jsonify({
        "error": "Too many requests. Please wait one minute and try again."
    }), 429


@app.errorhandler(sqlite3.Error)
def database_error(error):
    app.logger.exception("Database request failed")
    return jsonify(error="Unable to complete your request. Please try again later."), 503


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
