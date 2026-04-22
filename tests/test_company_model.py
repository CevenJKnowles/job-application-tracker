"""Tests for jat/models/company.py using an in-memory SQLite database."""

import sqlite3
from contextlib import contextmanager

import pytest

import jat.database.schema as schema_mod
import jat.models.company as company_model


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

    # Build the full schema on the in-memory connection, then apply migrations
    monkeypatch.setattr(schema_mod, "get_connection", _fake_get_connection)
    schema_mod.create_tables()
    schema_mod.run_migrations(conn)

    # Wire the company model to the same connection for all tests
    monkeypatch.setattr(company_model, "get_connection", _fake_get_connection)

    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_application(conn, company_id: int) -> None:
    """Insert a minimal application row satisfying all NOT NULL constraints."""
    conn.execute(
        "INSERT INTO applications (company_id, role_title, application_date)"
        " VALUES (?, 'Engineer', '2024-01-01')",
        (company_id,),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# add_company
# ---------------------------------------------------------------------------


def test_add_company_returns_int_id(mem_conn):
    """add_company returns an integer id >= 1."""
    new_id = company_model.add_company("Acme")
    assert isinstance(new_id, int)
    assert new_id >= 1


def test_add_company_id_matches_get_company_by_id(mem_conn):
    """The returned id retrieves the correct row via get_company_by_id."""
    new_id = company_model.add_company("Acme")
    row = company_model.get_company_by_id(new_id)
    assert row is not None
    assert row["id"] == new_id
    assert row["company_name"] == "Acme"


def test_add_company_duplicate_exact_case_raises(mem_conn):
    """Adding a company with an identical name raises ValueError."""
    company_model.add_company("Acme")
    with pytest.raises(ValueError, match="Company name already exists."):
        company_model.add_company("Acme")


def test_add_company_duplicate_different_case_raises(mem_conn):
    """Case-insensitive duplicate check: 'acme' conflicts with 'Acme'."""
    company_model.add_company("Acme")
    with pytest.raises(ValueError, match="Company name already exists."):
        company_model.add_company("acme")


# ---------------------------------------------------------------------------
# get_all_companies
# ---------------------------------------------------------------------------


def test_get_all_companies_ordered_by_name(mem_conn):
    """get_all_companies returns rows in ascending company_name order."""
    company_model.add_company("Zebra Inc")
    company_model.add_company("Acme Corp")
    company_model.add_company("Beta LLC")

    rows = company_model.get_all_companies()
    names = [r["company_name"] for r in rows]
    assert names == sorted(names)


def test_get_all_companies_application_count_zero(mem_conn):
    """A newly added company has application_count == 0."""
    company_model.add_company("Fresh Co")
    rows = company_model.get_all_companies()
    assert rows[0]["application_count"] == 0


# ---------------------------------------------------------------------------
# update_company
# ---------------------------------------------------------------------------


def test_update_company_changes_fields(mem_conn):
    """update_company persists changes to name, industry, website, and notes."""
    cid = company_model.add_company("Old Name", industry="Finance")
    company_model.update_company(
        cid,
        company_name="New Name",
        industry="Technology",
        website="https://new.example.com",
        notes="Updated notes",
    )
    row = company_model.get_company_by_id(cid)
    assert row["company_name"] == "New Name"
    assert row["industry"] == "Technology"
    assert row["website"] == "https://new.example.com"
    assert row["notes"] == "Updated notes"


def test_update_company_conflict_with_another_raises(mem_conn):
    """Renaming a company to the name of another company raises ValueError."""
    company_model.add_company("Alpha")
    cid = company_model.add_company("Beta")
    with pytest.raises(ValueError, match="Company name already exists."):
        company_model.update_company(cid, company_name="Alpha")


def test_update_company_keeping_own_name_does_not_raise(mem_conn):
    """Updating a company while keeping its existing name does not raise."""
    cid = company_model.add_company("Gamma", industry="Old Industry")
    company_model.update_company(cid, company_name="Gamma", industry="New Industry")
    row = company_model.get_company_by_id(cid)
    assert row["industry"] == "New Industry"


# ---------------------------------------------------------------------------
# delete_company
# ---------------------------------------------------------------------------


def test_delete_company_removes_row(mem_conn):
    """delete_company removes the row; subsequent get_company_by_id returns None."""
    cid = company_model.add_company("Deletable Co")
    company_model.delete_company(cid)
    assert company_model.get_company_by_id(cid) is None


def test_delete_company_with_linked_applications_raises(mem_conn):
    """delete_company raises ValueError when applications reference the company."""
    cid = company_model.add_company("Linked Co")
    _add_application(mem_conn, cid)
    with pytest.raises(ValueError, match="Cannot delete a company with linked applications."):
        company_model.delete_company(cid)


# ---------------------------------------------------------------------------
# search_companies
# ---------------------------------------------------------------------------


def test_search_companies_matches_name_case_insensitive(mem_conn):
    """search_companies returns rows whose company_name contains the query."""
    company_model.add_company("Acme Corporation")
    company_model.add_company("Widgets Ltd")

    results = company_model.search_companies("acme")
    names = [r["company_name"] for r in results]
    assert "Acme Corporation" in names
    assert "Widgets Ltd" not in names


def test_search_companies_matches_industry_case_insensitive(mem_conn):
    """search_companies returns rows whose industry contains the query."""
    company_model.add_company("TechCo", industry="Technology")
    company_model.add_company("BankCo", industry="Finance")

    results = company_model.search_companies("tech")
    names = [r["company_name"] for r in results]
    assert "TechCo" in names
    assert "BankCo" not in names


def test_search_companies_no_match_returns_empty(mem_conn):
    """search_companies returns an empty list when no rows match the query."""
    company_model.add_company("Alpha")
    company_model.add_company("Beta")

    results = company_model.search_companies("zzz_no_match")
    assert results == []


# ---------------------------------------------------------------------------
# get_company_application_count
# ---------------------------------------------------------------------------


def test_get_company_application_count_correct(mem_conn):
    """get_company_application_count returns the exact number of linked applications."""
    cid = company_model.add_company("Count Co")
    _add_application(mem_conn, cid)
    _add_application(mem_conn, cid)

    count = company_model.get_company_application_count(cid)
    assert count == 2
