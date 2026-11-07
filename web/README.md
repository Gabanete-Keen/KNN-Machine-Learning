# PAHUWAY

Flask serves the existing HTML/CSS/JavaScript website and KNN model. Open the site
through Flask; opening HTML files directly cannot use authentication.

## Run locally (PowerShell)

Install Python 3.12, then run from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000. Create an account at `/sign-up.html`, then sign in.
Passwords must contain 15–128 characters. No default account or mock login exists.
If the project-local testing runtime is present, it can also run the app:

```powershell
.\.runtime\python\python.exe app.py
```

## Database and configuration

The existing SQLite configuration is reused: `instance/pahuway.db`, outside the
public `web` directory. Startup initializes missing tables and applies repeatable,
additive migrations. `python database.py` also initializes the schema. Existing
users are preserved. There are no roles in the existing schema or application.

Tables: `users` (existing), `auth_sessions`, `assessments`, `schema_migrations`.
History stores the prediction and timestamp, not submitted answers. The dashboard
shows the latest 50 saved assessments belonging to the current user.

Optional environment variables (see `.env.example`; `.env` is not automatically loaded):

- `DATABASE_PATH`: override with the absolute path to an existing SQLite file.
- `AUTH_SESSION_SECONDS`: absolute session lifetime; default 28800 (8 hours).
- `SESSION_COOKIE_SECURE`: `0` for local HTTP; set `1` when deploying with HTTPS.
- `APP_ORIGIN`: public origin, such as `https://example.com`, for origin checks
  behind a reverse proxy. Defaults to the request origin locally.

Frontend and API share an origin. No CORS setup or separate frontend server is
needed. Deploy through a production WSGI server with HTTPS; `app.py` starts a
local development server. The existing limiter uses in-memory counters;
multiple production workers require a shared limiter store and trusted proxy/IP
configuration appropriate for the hosting setup. Back up `instance/`.

## Authentication flow

1. Signup posts name, email, and password to `/api/signup`. Email is normalized and
   unique; passwords are hashed with Argon2id. Signup does not log the user in.
2. Login posts credentials to `/api/login`; the database hash must verify. Existing
   Werkzeug scrypt/PBKDF2 hashes are verified and upgraded to Argon2id on login.
3. The server creates a random session token, stores only its SHA-256 digest in
   SQLite, and sends the token as an HttpOnly, SameSite=Lax cookie. Login rotates
   the current token. Session identity and expiration stay on the server.
4. The browser redirects to `/dashboard`, reusing the existing results page.
   Flask checks authentication before serving it. `/api/session` and `/api/history`
   also require an unexpired session. Refresh and server restarts retain sessions.
5. `/api/session` supplies a CSRF token held in JavaScript memory. Authenticated
   POST requests must include it. JSON-only endpoints and origin checks also block
   cross-origin submissions. Personal API and HTML responses use `Cache-Control: no-store`.
6. Logout posts to `/api/logout`, revokes the database session, clears the cookie
   and the temporary guest result, then returns to sign-in. A copied token stops
   working after logout or expiration.

Guest assessments remain available as promised on the homepage. `/results.html`
shows only the current tab's guest result; `/dashboard` displays private server
history. Signed-in predictions are saved to the account and survive refresh.
The navigation's existing Sign in link becomes Sign out after authentication.
Login/signup show loading and error messages and retain visibility toggles.
No CSS, page layout, or styling has been changed.

Password reset email is still explicitly a preview: no mail service or recovery
flow is configured. This implementation does not claim to send reset emails.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use temporary SQLite databases. Coverage includes hashing, duplicates,
invalid credentials/input, legacy account migration, cookies, CSRF, rotation,
refresh, expiration, logout/replayed tokens, protected routes, private history,
real model predictions, guest compatibility, and rate limiting.
The model requires scikit-learn 1.6.1, matching its saved training version.

Manual browser check: create an account, try a wrong password, sign in, refresh the
dashboard, complete the assessment, verify history persists, sign out, then open
`/dashboard` again. It must redirect to sign-in. A different account must not see
the first account's history.

An automated real-browser check is also available with Node.js 22+ and Chrome:

```powershell
node tests/browser_auth.cjs
```

It starts an isolated Flask server and headless Chrome, uses a separate database
under ignored `test-results/`, and stops both processes when finished. Override
`PYTHON_EXE` and `CHROME_PATH` if the executables are installed elsewhere. This
check exercises the actual forms, password toggle, invalid-login feedback,
dashboard refresh, assessment submission, saved history, and logout.
