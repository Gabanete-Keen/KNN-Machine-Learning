from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


from pathlib import Path
import math

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

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


# Track requests using the caller's IP address.
# Counters are stored in memory and reset when the server restarts.
# Enable response headers that describe the request limits.
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://",
    headers_enabled=True,
)


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

        return jsonify({
            "stress_level": str(prediction),
        })

    except Exception:
        app.logger.exception("Prediction failed")
        return jsonify({
            "error": "Unable to calculate a prediction."
        }), 500

# Return a readable JSON message when a request exceeds 4 KB.
# HTTP 413 means the request body is too large.
@app.errorhandler(413)
def request_too_large(error):
    return jsonify({
        "error": "Request too large. Submit only your assessment answers."
    }), 413


# Return a readable JSON message when the request limit is exceeded.
# HTTP 429 means too many requests were sent.
@app.errorhandler(429)
def too_many_requests(error):
    return jsonify({
        "error": "Too many requests. Please wait one minute and try again."
    }), 429


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)