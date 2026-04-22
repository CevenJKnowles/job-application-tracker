"""Tests for jat/database/schema.py and seed.py using an in-memory SQLite database."""

import sqlite3
from contextlib import contextmanager

import pytest

import jat.database.schema as schema_mod
import jat.database.seed as seed_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_conn(monkeypatch):
    """Patch get_connection so all schema and seed calls share one in-memory DB."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    @contextmanager
    def _fake_get_connection():
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    monkeypatch.setattr(schema_mod, "get_connection", _fake_get_connection)
    monkeypatch.setattr(seed_mod, "get_connection", _fake_get_connection)

    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXPECTED_TABLES = {
    "ref_statuses",
    "ref_categories",
    "ref_employment_types",
    "ref_sources",
    "ref_work_modes",
    "ref_currencies",
    "companies",
    "applications",
}

_REF_TABLES = [
    "ref_statuses",
    "ref_categories",
    "ref_employment_types",
    "ref_sources",
    "ref_work_modes",
    "ref_currencies",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_schema_creates_all_tables(db_conn):
    """create_tables creates all 8 expected tables."""
    schema_mod.create_tables()
    tables = {
        row[0]
        for row in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert _EXPECTED_TABLES.issubset(tables)


def test_schema_is_idempotent(db_conn):
    """Calling create_tables twice raises no exception and all tables remain."""
    schema_mod.create_tables()
    schema_mod.create_tables()
    tables = {
        row[0]
        for row in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert _EXPECTED_TABLES.issubset(tables)


def test_seed_defaults_populates_ref_tables(db_conn):
    """seed_defaults inserts at least one row into each ref_ table."""
    schema_mod.create_tables()
    schema_mod.run_migrations(db_conn)
    seed_mod.seed_defaults()
    for table in _REF_TABLES:
        count = db_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count > 0, f"{table} is empty after seeding"


def test_seed_defaults_is_idempotent(db_conn):
    """Calling seed_defaults twice produces identical row counts in all ref_ tables."""
    schema_mod.create_tables()
    schema_mod.run_migrations(db_conn)
    seed_mod.seed_defaults()
    counts_first = {
        t: db_conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in _REF_TABLES
    }
    seed_mod.seed_defaults()
    counts_second = {
        t: db_conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in _REF_TABLES
    }
    assert counts_first == counts_second


def test_run_migrations_is_idempotent(db_conn):
    """Calling run_migrations three times on the same connection raises no exception."""
    schema_mod.create_tables()
    schema_mod.run_migrations(db_conn)
    schema_mod.run_migrations(db_conn)
    schema_mod.run_migrations(db_conn)


def test_companies_notes_column_exists(db_conn):
    """companies.notes column is present after create_tables and run_migrations."""
    schema_mod.create_tables()
    schema_mod.run_migrations(db_conn)
    columns = {
        row["name"] for row in db_conn.execute("PRAGMA table_info(companies)")
    }
    assert "notes" in columns


def test_ref_statuses_funnel_order_column_exists(db_conn):
    """ref_statuses.funnel_order column is present after create_tables and run_migrations."""
    schema_mod.create_tables()
    schema_mod.run_migrations(db_conn)
    columns = {
        row["name"] for row in db_conn.execute("PRAGMA table_info(ref_statuses)")
    }
    assert "funnel_order" in columns
