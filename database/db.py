"""
Database connection helper for MediAssist AI.
Provides a single point of access to the SQLite database with
row-factory dictionaries for easy JSON serialization.
"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "mediassist.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")


def get_connection():
    """Return a new SQLite connection with dict-like row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_columns(conn, table, columns):
    """
    Lightweight migration helper: adds any missing columns to an
    already-existing table. Needed because schema.sql uses
    'CREATE TABLE IF NOT EXISTS', which won't add new columns to a
    table that was created by an older version of the schema.
    """
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for col_name, col_def in columns:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")


def init_db():
    """Create all tables from schema.sql if the database does not exist."""
    first_time = not os.path.exists(DB_PATH)
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())

    # Migrate older databases that predate the input_mode/lang columns.
    _ensure_columns(conn, "chat_logs", [
        ("input_mode", "TEXT DEFAULT 'text'"),
        ("lang", "TEXT DEFAULT 'en'"),
    ])

    # Migrate older databases that predate the bills.category column
    # (added for the patient-wise billing history / breakdown feature).
    _ensure_columns(conn, "bills", [
        ("category", "TEXT DEFAULT 'consultation'"),
    ])

    conn.commit()
    conn.close()
    return first_time


def query(sql, params=(), fetchone=False, commit=False):
    """Generic helper to run a query and return results as list[dict]."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    if commit:
        conn.commit()
        last_id = cur.lastrowid
        conn.close()
        return last_id
    rows = cur.fetchone() if fetchone else cur.fetchall()
    conn.close()
    if rows is None:
        return None
    if fetchone:
        return dict(rows)
    return [dict(r) for r in rows]
