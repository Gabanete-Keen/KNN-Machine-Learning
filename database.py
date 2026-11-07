import sqlite3
import os
from pathlib import Path

# Store the database outside the publicly served web folder.
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "instance" / "pahuway.db"


def get_connection():
    database_path = Path(os.environ.get("DATABASE_PATH", str(DATABASE_PATH)))
    # Create the instance folder if it does not exist.
    database_path.parent.mkdir(parents=True, exist_ok=True)

    # Open a connection to the SQLite database.
    connection = sqlite3.connect(database_path, timeout=10)

    # Allow reading columns by name, such as user["email"].
    connection.row_factory = sqlite3.Row

    # Enforce foreign-key relationships for future tables.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    connection = get_connection()

    try:
        # Create the users table without deleting existing accounts.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                display_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Additive, repeatable migration: existing user rows remain untouched.
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                csrf_token TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS sessions_expiry ON auth_sessions(expires_at);
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                stress_level TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS assessments_user ON assessments(user_id, id);
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO schema_migrations(version) VALUES (1);
        """)
        connection.commit()

    finally:
        # Always close the connection after setup.
        connection.close()


# Initialize the database when this file is run directly.
if __name__ == "__main__":
    initialize_database()
