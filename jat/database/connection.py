"""SQLite connection manager for the Job Application Tracker database."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "jat.db"


@contextmanager
def get_connection():
    """Yield a sqlite3.Connection to data/jat.db with row_factory and foreign keys enabled."""
    connection = sqlite3.connect(_DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
