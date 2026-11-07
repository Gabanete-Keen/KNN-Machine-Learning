import importlib
import time
from contextlib import closing

import pytest
from werkzeug.security import generate_password_hash

PASSWORD = "correct horse battery staple"
ANSWERS = {"Sleep_Hours": 7, "Screen_Time": 5, "Assignment_Load": 4,
           "Exam_Pressure": 5, "Social_Support": 7}


@pytest.fixture
def server(tmp_path, monkeypatch):
    # Never run tests against the developer's database.
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    import database
    database.initialize_database()
    module = importlib.import_module("app")
    module.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    module.limiter.reset()
    return module


def signup(client, email="student@example.com"):
    return client.post("/api/signup", json={"display_name": "Student",
                       "email": email, "password": PASSWORD})


def login(client, email="student@example.com", password=PASSWORD):
    return client.post("/api/login", json={"email": email, "password": password})


def csrf(client):
    return {"X-CSRF-Token": client.get("/api/session").json["csrf_token"]}


def test_registration_and_real_login(server):
    client = server.app.test_client()
    assert signup(client).status_code == 201
    from database import get_connection
    with closing(get_connection()) as db:
        user = db.execute("SELECT * FROM users").fetchone()
        assert user["password_hash"].startswith("$argon2id$")
        assert PASSWORD not in user["password_hash"]
        assert server.password_hasher.verify(user["password_hash"], PASSWORD)
    assert signup(client, "STUDENT@example.com").status_code == 409
    assert login(client, password="incorrect").status_code == 401
    assert login(client, email="missing@example.com").status_code == 401
    assert client.post("/api/login", json={}).status_code == 400
    assert client.post("/api/login", json={"email": [], "password": 1}).status_code == 400
    response = login(client, email=" STUDENT@example.com ")
    assert response.status_code == 200
    assert response.json["redirect"] == "/dashboard"
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Max-Age=28800" in cookie
    with closing(get_connection()) as db:
        stored = db.execute("SELECT * FROM auth_sessions").fetchone()
        raw = client.get_cookie("pahuway_session").value
        assert stored["token_hash"] != raw
        assert stored["token_hash"] == server.token_digest(raw)


def test_protection_refresh_logout_replay(server):
    client = server.app.test_client()
    assert client.get("/dashboard").status_code == 302
    assert client.get("/api/history").status_code == 401
    assert client.get("/api/session").status_code == 401
    signup(client)
    login(client)
    token = client.get_cookie("pahuway_session").value
    assert client.get("/dashboard").status_code == 200
    assert client.get("/dashboard").status_code == 200  # Refresh
    assert client.get("/api/session").json["user"]["email"] == "student@example.com"
    other_tab = server.app.test_client()
    other_tab.set_cookie("pahuway_session", token)
    assert other_tab.get("/api/session").status_code == 200
    assert client.post("/api/logout", json={}).status_code == 403
    assert client.post("/api/logout", json={}, headers=csrf(client)).status_code == 200
    assert client.get_cookie("pahuway_session") is None
    assert other_tab.get("/api/session").status_code == 401
    assert other_tab.get("/dashboard").status_code == 302


def test_expiration_and_session_rotation(server):
    client = server.app.test_client()
    signup(client)
    login(client)
    old = client.get_cookie("pahuway_session").value
    assert client.post("/api/login", json={"email": "student@example.com", "password": PASSWORD},
                       headers=csrf(client)).status_code == 200
    replay = server.app.test_client()
    replay.set_cookie("pahuway_session", old)
    assert replay.get("/api/session").status_code == 401
    from database import get_connection
    with closing(get_connection()) as db:
        db.execute("UPDATE auth_sessions SET expires_at = ?", (int(time.time()) - 1,))
        db.commit()
    assert client.get("/api/session").status_code == 401
    assert client.get("/dashboard").status_code == 302


def test_csrf_validation_and_cookie_security(server):
    client = server.app.test_client()
    assert client.post("/api/login", json={"email": "a@b.co", "password": PASSWORD},
                       headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/signup", data="email=x").status_code == 415
    assert client.post("/api/signup", json=[]).status_code == 400
    assert client.post("/api/signup", json={"display_name": "A", "email": "bad", "password": PASSWORD}).status_code == 400
    assert client.post("/api/signup", json={"display_name": "A", "email": "a@b.co", "password": "short"}).status_code == 400
    signup(client)
    server.app.config["SESSION_COOKIE_SECURE"] = True
    response = login(client)
    assert "Secure;" in response.headers["Set-Cookie"]
    assert client.post("/api/predict", json=ANSWERS).status_code == 403
    assert client.post("/api/predict", json=ANSWERS, headers={"X-CSRF-Token": "invalid"}).status_code == 403
    assert client.post("/api/signup", data="x" * 5000, content_type="application/json",
                       headers=csrf(client)).status_code == 413


def test_history_is_private_and_guest_predictions_preserved(server):
    guest = server.app.test_client()
    assert guest.get("/results.html").status_code == 200
    assert guest.post("/api/predict", json=ANSWERS).status_code == 200
    client = server.app.test_client()
    signup(client)
    login(client)
    response = client.post("/api/predict", json=ANSWERS, headers=csrf(client))
    assert response.status_code == 200
    history = client.get("/api/history").json["results"]
    assert len(history) == 1
    assert history[0]["stress_level"] == response.json["stress_level"]
    another = server.app.test_client()
    signup(another, "another@example.com")
    login(another, "another@example.com")
    assert another.get("/api/history").json["results"] == []
    assert client.get("/api/history").headers["Cache-Control"] == "no-store"
    assert guest.post("/api/predict", json={}).status_code == 400


def test_additive_migration_preserves_legacy_account(server):
    from database import get_connection, initialize_database
    with closing(get_connection()) as db:
        db.execute("INSERT INTO users(display_name, email, password_hash) VALUES (?, ?, ?)",
                   ("Legacy", "legacy@example.com", generate_password_hash(PASSWORD, method="scrypt")))
        db.commit()
        original = dict(db.execute("SELECT * FROM users").fetchone())
    initialize_database()
    initialize_database()
    with closing(get_connection()) as db:
        assert dict(db.execute("SELECT * FROM users").fetchone()) == original
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert login(server.app.test_client(), "legacy@example.com").status_code == 200
    with closing(get_connection()) as db:
        updated = dict(db.execute("SELECT * FROM users").fetchone())
        assert updated["password_hash"].startswith("$argon2id$")
        assert all(updated[k] == original[k] for k in original if k != "password_hash")


def test_login_rate_limit(server):
    client = server.app.test_client()
    for _ in range(10):
        assert client.post("/api/login", json={}).status_code == 400
    response = client.post("/api/login", json={})
    assert response.status_code == 429
    assert "error" in response.json
