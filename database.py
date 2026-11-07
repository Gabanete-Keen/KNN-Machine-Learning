import sqlite3
from pathlib import Path

# Store the database outside the publicly served web folder.
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "instance" / "pahuway.db"


def get_connection():
    # Create the instance folder if it does not exist.
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Open a connection to the SQLite database.
    connection = sqlite3.connect(DATABASE_PATH)

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

        connection.commit()
        print("Database initialized successfully.")

    finally:
        # Always close the connection after setup.
        connection.close()


# Initialize the database when this file is run directly.
if __name__ == "__main__":
    initialize_database()