# PAHUWAY

PAHUWAY is a student stress prediction prototype built with Flask,
HTML, CSS, JavaScript, SQLite, and a trained K-Nearest Neighbors (KNN) model.

It supports wellness awareness only and is not a medical diagnosis.

## Features

- Complete a five-question stress assessment.
- Receive a Low, Medium, or High stress prediction.
- Create an account and sign in.
- Save assessment results when signed in.
- View your latest 50 saved results.
- Sign out of your account.
- Complete assessments as a guest without registering.

Password reset is currently a preview. Reset emails are not sent.

## Requirements

- Python 3.12
- pip
- A web browser

The trained model requires scikit-learn 1.6.1.
This version is included in requirements.txt.

## Project Structure

    KNN-Machine-Learning/
    ├── app.py
    ├── database.py
    ├── requirements.txt
    ├── requirements-dev.txt
    ├── .env.example
    ├── .gitignore
    ├── model/
    │   └── stress_knn_bundle.joblib
    ├── instance/
    │   └── pahuway.db
    ├── tests/
    │   ├── test_auth.py
    │   └── browser_auth.cjs
    └── web/
        ├── README.md
        ├── index.html
        ├── TakeTest.html
        ├── TakeTest.js
        ├── results.html
        ├── results.js
        ├── sign-in.html
        ├── sign-up.html
        ├── forgot-password.html
        ├── auth.js
        ├── session.js
        ├── navigation.js
        ├── tips.html
        └── styling/

The instance folder and database are created locally and excluded from Git.

## First-Time Setup

Open PowerShell in the project root, where app.py is located.

```powershell
# Create a virtual environment using Python 3.12.
py -3.12 -m venv .venv312

# Install the project's dependencies.
.\.venv312\Scripts\python.exe -m pip install -r requirements.txt

# Start the Flask application.
.\.venv312\Scripts\python.exe app.py
```

Open this address in your browser:

http://127.0.0.1:5000

Keep the terminal running while using the website.
Press Ctrl + C in that terminal to stop the server.

Open the website through Flask. Opening HTML files directly or using
VS Code Live Server will not connect to the backend correctly.

## Running the Project Again

You do not need to recreate the virtual environment every time.

```powershell
# Start the website using the existing Python 3.12 environment.
.\.venv312\Scripts\python.exe app.py
```

After pulling changes that update requirements.txt, install the dependencies again:

```powershell
# Install any new or updated dependencies.
.\.venv312\Scripts\python.exe -m pip install -r requirements.txt
```

If Python reports that the argon2 module is missing, run the command above.
The package that provides this module is named argon2-cffi.

## Assessment Inputs

The model uses these five selected features:

| Feature | Input type | Supported range |
| --- | --- | --- |
| Sleep_Hours | Hours per day | 4–9 |
| Screen_Time | Hours per day | 2–10 |
| Assignment_Load | Whole-number rating | 1–9 |
| Exam_Pressure | Whole-number rating | 1–10 |
| Social_Support | Whole-number rating | 1–10 |

The website accepts hours with up to one decimal place.
Higher ratings represent greater assignment load, exam pressure, or social support.

These ranges are the current prototype's supported limits.
Users should not change their actual answers just to fit these limits.

The frontend checks inputs before submission.
The backend independently validates field names, numeric values, ranges,
and whole-number ratings.

## How Prediction Works

1. The website collects the five assessment answers.
2. JavaScript sends them to POST /api/predict.
3. Flask validates the submitted data.
4. Flask arranges the data in the original feature order.
5. The saved pipeline applies preprocessing, feature selection, and KNN prediction.
6. The server returns Low, Medium, or High.
7. The website displays the result.

The saved pipeline expects the original 11-column structure.
The six unselected columns are supplied as missing values, and the saved
pipeline handles preprocessing and selects the five required features.

The application loads the trained model from:

    model/stress_knn_bundle.joblib

Only load a trusted model file. Joblib files can execute code when loaded.

## Accounts and Sessions

Signup requires a display name, email address, and a password containing
15–128 characters.

- Email addresses are normalized and must be unique.
- New passwords are stored as Argon2id hashes.
- Existing supported Werkzeug password hashes are upgraded after successful login.
- Creating an account does not automatically sign the user in.
- Login creates a server-side session with an eight-hour default lifetime.
- The browser receives an HttpOnly, SameSite=Lax session cookie.
- The database stores a digest of the session token.
- Logout revokes the current session and clears its cookie.

The dashboard and history API require an active session.
History queries use the signed-in user's ID to keep account histories separate.

## Results and Database Storage

Guest predictions do not create assessment records in the database.
The latest result is stored temporarily in the browser tab using sessionStorage.

For signed-in users, the database stores the predicted stress level and timestamp.
It does not store the five submitted assessment answers.

Starting another assessment clears the temporary result in the current tab.
It does not delete saved account history.

The default database location is:

    instance/pahuway.db

The database contains:

| Table | Purpose |
| --- | --- |
| users | Account details and password hashes |
| auth_sessions | Session token digests, CSRF tokens, and expiration times |
| assessments | Saved predictions belonging to users |
| schema_migrations | Applied database schema versions |

Application startup creates missing tables without deleting existing accounts.

To initialize the database manually:

```powershell
# Create any missing database tables.
.\.venv312\Scripts\python.exe database.py
```

Do not commit the database or real user records to GitHub.
Back up the database before making schema changes.

## API Routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | /api/health | Check model readiness and required inputs |
| POST | /api/signup | Create an account |
| POST | /api/login | Verify credentials and create a session |
| GET | /api/session | Retrieve the current user and CSRF token |
| POST | /api/logout | Revoke the current session |
| POST | /api/predict | Calculate a stress prediction |
| GET | /api/history | Retrieve the current user's latest 50 results |
| GET | /dashboard | Display the signed-in user's history page |

## Existing Protections

- Parameterized SQL queries keep submitted values separate from SQL commands.
- Password hashing avoids storing plaintext passwords.
- Backend validation rejects invalid or unexpected inputs.
- Request bodies are limited to 4 KB.
- Signup is limited to five requests per minute per IP address.
- Login and prediction are each limited to ten requests per minute per IP address.
- Authenticated API POST requests require a CSRF token.
- API write requests require JSON and undergo origin checks.
- Personal API and HTML responses use Cache-Control: no-store.
- Security headers discourage framing and content-type guessing.

Rate limits reduce repeated requests; they do not make a public API private.

Rate-limit counters currently use memory. They reset when the server restarts
and are not shared between separate server processes.

## Configuration

Optional environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| DATABASE_PATH | Override the SQLite database location | instance/pahuway.db |
| AUTH_SESSION_SECONDS | Session lifetime in seconds | 28800 |
| SESSION_COOKIE_SECURE | Use secure cookies with HTTPS when set to 1 | 0 |
| APP_ORIGIN | Expected website origin for origin checks | Request origin |

See .env.example for examples.

The application does not automatically load a .env file.
Set variables in the terminal or hosting environment before starting Flask.

For example, for local development:

```powershell
# Allow the session cookie on local HTTP.
$env:SESSION_COOKIE_SECURE = "0"

# Set the expected local website origin.
$env:APP_ORIGIN = "http://127.0.0.1:5000"

# Start Flask with these settings.
.\.venv312\Scripts\python.exe app.py
```

## Backend Tests

Run these commands from the project root:

```powershell
# Install the test dependencies.
.\.venv312\Scripts\python.exe -m pip install -r requirements-dev.txt

# Run the automated backend tests.
.\.venv312\Scripts\python.exe -m pytest -q
```

Tests use temporary SQLite databases rather than the application's normal database.

They cover account creation, password verification, legacy password upgrades,
session behavior, CSRF checks, private history, guest predictions, and login
rate limiting.

## Manual Browser Checks

1. Create an account.
2. Try signing in with an incorrect password.
3. Sign in with the correct password.
4. Complete an assessment.
5. Refresh the dashboard and confirm the result remains.
6. Sign out.
7. Open /dashboard and confirm it redirects to sign-in.
8. Sign in with a different account and confirm the histories are separate.
9. Sign out and confirm guest assessments still work.

## Optional Automated Browser Test

This test requires Node.js 22 or later and Google Chrome.

```powershell
# Select the project's Python 3.12 environment for the browser test.
$env:PYTHON_EXE = (Resolve-Path ".\.venv312\Scripts\python.exe").Path

# Run the browser test.
node tests/browser_auth.cjs
```

If Chrome is installed somewhere other than the test's default path,
set CHROME_PATH to the full path of chrome.exe before running the test.

The test starts a separate Flask server and browser.
It uses a separate database under test-results/ and stops its processes afterward.

## Current Limitations

- Password reset emails are not implemented.
- Signup does not verify ownership of an email address.
- Predictions are limited to the prototype's supported input ranges.
- The dashboard displays only the latest 50 saved assessments.
- Rate-limit counters use process memory.
- Predictions support wellness awareness and are not clinical diagnoses.

## Deployment Notes

The command python app.py starts a local development server.

Before public deployment:

- Use a production WSGI server and HTTPS.
- Set SESSION_COOKIE_SECURE=1.
- Set APP_ORIGIN to the actual website origin.
- Use a shared rate-limit store if running multiple workers.
- Configure trusted proxy handling for the hosting environment.
- Keep the database outside the public web directory.
- Keep credentials and private configuration out of Git.
- Maintain database backups.