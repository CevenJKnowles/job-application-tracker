"""Tests for jat/models/application.py using an in-memory SQLite database."""

import sqlite3
from contextlib import contextmanager

import pytest

import jat.database.schema as schema_mod
import jat.database.seed as seed_mod
import jat.models.application as application_model


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_conn(monkeypatch):
    """Patch get_connection so all model and schema calls share one in-memory DB."""
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
    schema_mod.create_tables()
    schema_mod.run_migrations(conn)

    monkeypatch.setattr(seed_mod, "get_connection", _fake_get_connection)
    seed_mod.seed_defaults()

    monkeypatch.setattr(application_model, "get_connection", _fake_get_connection)

    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_company(conn, name: str = "Test Co") -> int:
    """Insert a minimal company row and return its company_id."""
    cursor = conn.execute(
        "INSERT INTO companies (company_name) VALUES (?)",
        (name,),
    )
    conn.commit()
    return cursor.lastrowid


# ---------------------------------------------------------------------------
# add_application / get_application_by_id
# ---------------------------------------------------------------------------


def test_add_application_returns_int_id(mem_conn):
    """add_application returns an integer id >= 1."""
    cid = _add_company(mem_conn)
    aid = application_model.add_application(cid, "Engineer", "2024-01-15")
    assert isinstance(aid, int)
    assert aid >= 1


def test_add_application_retrieved_by_id(mem_conn):
    """The returned id retrieves the correct row via get_application_by_id."""
    cid = _add_company(mem_conn)
    aid = application_model.add_application(cid, "Designer", "2024-02-10")
    row = application_model.get_application_by_id(aid)
    assert row is not None
    assert row["application_id"] == aid
    assert row["role_title"] == "Designer"
    assert row["company_id"] == cid


# ---------------------------------------------------------------------------
# get_all_applications
# ---------------------------------------------------------------------------


def test_get_all_applications_newest_first(mem_conn):
    """get_all_applications returns rows ordered by application_date DESC."""
    cid = _add_company(mem_conn)
    application_model.add_application(cid, "Old Role", "2024-01-01")
    application_model.add_application(cid, "New Role", "2024-06-01")
    application_model.add_application(cid, "Mid Role", "2024-03-01")

    rows = application_model.get_all_applications()
    dates = [r["application_date"] for r in rows]
    assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# update_application
# ---------------------------------------------------------------------------


def test_update_application_single_field(mem_conn):
    """update_application persists a change to a single field."""
    cid = _add_company(mem_conn)
    aid = application_model.add_application(cid, "Old Title", "2024-01-01")
    application_model.update_application(aid, role_title="New Title")
    row = application_model.get_application_by_id(aid)
    assert row["role_title"] == "New Title"


def test_update_application_multiple_fields(mem_conn):
    """update_application persists changes to several fields at once."""
    cid = _add_company(mem_conn)
    aid = application_model.add_application(cid, "Original", "2024-01-01")
    application_model.update_application(
        aid, role_title="Updated", city="London", country="UK"
    )
    row = application_model.get_application_by_id(aid)
    assert row["role_title"] == "Updated"
    assert row["city"] == "London"
    assert row["country"] == "UK"


def test_update_application_changes_updated_at(mem_conn):
    """update_application always refreshes updated_at away from a forced old value."""
    cid = _add_company(mem_conn)
    aid = application_model.add_application(cid, "Role", "2024-01-01")
    mem_conn.execute(
        "UPDATE applications SET updated_at = '2000-01-01 00:00:00'"
        " WHERE application_id = ?",
        (aid,),
    )
    mem_conn.commit()
    application_model.update_application(aid, notes="changed")
    row = application_model.get_application_by_id(aid)
    assert row["updated_at"] != "2000-01-01 00:00:00"


def test_update_application_no_fields_raises(mem_conn):
    """update_application raises ValueError when called with no kwargs."""
    cid = _add_company(mem_conn)
    aid = application_model.add_application(cid, "Role", "2024-01-01")
    with pytest.raises(ValueError):
        application_model.update_application(aid)


def test_update_application_nonexistent_raises(mem_conn):
    """update_application raises ValueError when application_id does not exist."""
    with pytest.raises(ValueError):
        application_model.update_application(9999, role_title="Ghost")


# ---------------------------------------------------------------------------
# delete_application
# ---------------------------------------------------------------------------


def test_delete_application_removes_row(mem_conn):
    """delete_application removes the row; get_application_by_id returns None."""
    cid = _add_company(mem_conn)
    aid = application_model.add_application(cid, "Temp Role", "2024-01-01")
    application_model.delete_application(aid)
    assert application_model.get_application_by_id(aid) is None


def test_delete_application_nonexistent_raises(mem_conn):
    """delete_application raises ValueError when application_id does not exist."""
    with pytest.raises(ValueError):
        application_model.delete_application(9999)


# ---------------------------------------------------------------------------
# search_applications
# ---------------------------------------------------------------------------


def test_search_matches_role_title(mem_conn):
    """search_applications returns rows whose role_title contains the query."""
    cid = _add_company(mem_conn)
    application_model.add_application(cid, "Senior Python Developer", "2024-01-01")
    application_model.add_application(cid, "Marketing Manager", "2024-01-02")

    results = application_model.search_applications("python")
    titles = [r["role_title"] for r in results]
    assert "Senior Python Developer" in titles
    assert "Marketing Manager" not in titles


def test_search_matches_notes(mem_conn):
    """search_applications returns rows whose notes contain the query."""
    cid = _add_company(mem_conn)
    application_model.add_application(
        cid, "Role A", "2024-01-01", notes="great culture fit"
    )
    application_model.add_application(
        cid, "Role B", "2024-01-02", notes="salary too low"
    )

    results = application_model.search_applications("great culture")
    titles = [r["role_title"] for r in results]
    assert "Role A" in titles
    assert "Role B" not in titles


def test_search_no_match_returns_empty(mem_conn):
    """search_applications returns an empty list when no rows match."""
    cid = _add_company(mem_conn)
    application_model.add_application(cid, "UX Designer", "2024-01-01")

    results = application_model.search_applications("zzz_no_match")
    assert results == []


# ---------------------------------------------------------------------------
# filter_applications
# ---------------------------------------------------------------------------


def test_filter_by_status_id(mem_conn):
    """filter_applications returns only rows matching the given status_id."""
    cid = _add_company(mem_conn)
    application_model.add_application(cid, "Role A", "2024-01-01", status_id=1)
    application_model.add_application(cid, "Role B", "2024-01-02", status_id=2)

    results = application_model.filter_applications(status_id=1)
    assert len(results) == 1
    assert all(r["status_id"] == 1 for r in results)


def test_filter_by_company_id(mem_conn):
    """filter_applications returns only rows for the given company_id."""
    cid1 = _add_company(mem_conn, "Company Alpha")
    cid2 = _add_company(mem_conn, "Company Beta")
    application_model.add_application(cid1, "Role at Alpha", "2024-01-01")
    application_model.add_application(cid2, "Role at Beta", "2024-01-02")

    results = application_model.filter_applications(company_id=cid1)
    assert len(results) == 1
    assert all(r["company_id"] == cid1 for r in results)


def test_filter_by_category_id(mem_conn):
    """filter_applications returns only rows matching the given category_id."""
    cid = _add_company(mem_conn)
    application_model.add_application(cid, "Design Role", "2024-01-01", category_id=1)
    application_model.add_application(cid, "Dev Role", "2024-01-02", category_id=2)

    results = application_model.filter_applications(category_id=1)
    assert len(results) == 1
    assert all(r["category_id"] == 1 for r in results)


def test_filter_no_args_raises(mem_conn):
    """filter_applications raises ValueError when called with no filter arguments."""
    with pytest.raises(ValueError):
        application_model.filter_applications()
