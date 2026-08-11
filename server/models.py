import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "wenyan.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS progress (
            user_id INTEGER PRIMARY KEY,
            data TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


def init_progress(user_id: int):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO progress (user_id, data, updated_at) VALUES (?, '{}', datetime('now'))",
        (user_id,)
    )
    conn.commit()
    conn.close()


def get_progress(user_id: int) -> dict:
    conn = get_db()
    row = conn.execute("SELECT data FROM progress WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        return json.loads(row["data"])
    return {}


def save_progress(user_id: int, data: dict):
    conn = get_db()
    conn.execute(
        "INSERT INTO progress (user_id, data, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(user_id) DO UPDATE SET data = excluded.data, updated_at = datetime('now')",
        (user_id, json.dumps(data, ensure_ascii=False))
    )
    conn.commit()
    conn.close()


def create_user(username: str, password_hash: str, created_at: str) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, password_hash, created_at)
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_username(username: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row
