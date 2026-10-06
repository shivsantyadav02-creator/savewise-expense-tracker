import sqlite3
from pathlib import Path
from flask import g
from config import Config

def get_db():
    """
    Returns a per-request SQLite connection.
    - Stored in Flask's application context global 'g'.
    - Enables PRAGMA foreign_keys = ON on EVERY connection (ensures CASCADE works).
    - Sets row_factory = sqlite3.Row so columns can be accessed by name (row['col']).
    """
    if "db" not in g:
        g.db = sqlite3.connect(Config.DATABASE_PATH)
        # CRITICAL: SQLite disables foreign keys by default. Always turn them ON!
        g.db.execute("PRAGMA foreign_keys = ON;")
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Closes the active database connection when the request finishes."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db(schema_path=None):
    """
    Executes schema.sql to create all tables, indexes, and initial seeds.
    Can be run from command line or app initialization.
    """
    if schema_path is None:
        schema_path = Path(__file__).resolve().parent / "schema.sql"
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()

def init_app(app):
    """Registers database lifecycle hooks with the Flask application."""
    app.teardown_appcontext(close_db)
