"""Tests for jat/analytics/queries.py using an in-memory SQLite database."""

import sqlite3
from contextlib import contextmanager

import pytest

import jat.database.schema as schema_mod
import jat.database.seed as seed_mod
from jat.analytics.queries import (
    applications_by_category,
    applications_by_status,
    applications_by_work_mode,
    applications_over_time,
    summary_stats,
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(monkeypatch):
    """In-memory SQLite connection with schema, migrations, seed data, and test rows."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.commit()

    @contextmanager
    def _fake_get_connection():
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    monkeypatch.setattr(schema_mod, "get_connection", _fake_get_connection)
    monkeypatch.setattr(seed_mod, "get_connection", _fake_get_connection)

    schema_mod.create_tables()
    schema_mod.run_migrations(db)
    seed_mod.seed_defaults()

    # One company required by the NOT NULL foreign key
    db.execute(
        "INSERT INTO companies (company_name) VALUES ('Test Co')"
    )
    db.commit()

    # 6 applications:
    #   statuses  — Applied(1)×2, Interview(3)×2, Rejected(6)×1, Offer(5)×1  → 4 statuses
    #   categories — Product Design(1)×3, UX/UI Design(2)×3                  → 2 categories
    #   work modes — Onsite(1)×3, Hybrid(2)×2, Remote(3)×1                   → 3 work modes
    #   months    — 2026-01×2, 2026-02×3, 2026-03×1                          → 3 periods
    #   response_date present: rows 2,3,5,6                                   → 4/6
    rows = [
        (1, "Role A", "2026-01-15", None, 1, 1, 1),       # Applied, Product Design, Onsite
        (1, "Role B", "2026-01-20", "2026-01-25", 1, 1, 2),  # Applied, Product Design, Hybrid
        (1, "Role C", "2026-02-01", "2026-02-05", 3, 2, 1),  # Interview, UX/UI, Onsite
        (1, "Role D", "2026-02-10", None, 3, 2, 2),        # Interview, UX/UI, Hybrid
        (1, "Role E", "2026-02-15", "2026-02-20", 6, 1, 1), # Rejected, Product Design, Onsite
        (1, "Role F", "2026-03-01", "2026-03-05", 5, 2, 3), # Offer, UX/UI, Remote
    ]
    db.executemany(
        """
        INSERT INTO applications
            (company_id, role_title, application_date, response_date,
             status_id, category_id, work_mode_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    db.commit()

    yield db
    db.close()


# ---------------------------------------------------------------------------
# applications_by_status
# ---------------------------------------------------------------------------


def test_applications_by_status_returns_list(conn):
    """applications_by_status returns a list."""
    result = applications_by_status(conn)
    assert isinstance(result, list)


def test_applications_by_status_known_value(conn):
    """applications_by_status includes Applied with count 2."""
    result = applications_by_status(conn)
    applied = next((r for r in result if r["label"] == "Applied"), None)
    assert applied is not None
    assert applied["count"] == 2


def test_applications_by_status_ordered_by_count_desc(conn):
    """applications_by_status is ordered from highest to lowest count."""
    result = applications_by_status(conn)
    counts = [r["count"] for r in result]
    assert counts == sorted(counts, reverse=True)


# ---------------------------------------------------------------------------
# applications_over_time
# ---------------------------------------------------------------------------


def test_applications_over_time_returns_list(conn):
    """applications_over_time returns a list."""
    result = applications_over_time(conn)
    assert isinstance(result, list)


def test_applications_over_time_known_period(conn):
    """applications_over_time includes 2026-01 with count 2."""
    result = applications_over_time(conn)
    jan = next((r for r in result if r["period"] == "2026-01"), None)
    assert jan is not None
    assert jan["count"] == 2


def test_applications_over_time_ordered_asc(conn):
    """applications_over_time periods are in ascending chronological order."""
    result = applications_over_time(conn)
    periods = [r["period"] for r in result]
    assert periods == sorted(periods)


# ---------------------------------------------------------------------------
# applications_by_category
# ---------------------------------------------------------------------------


def test_applications_by_category_returns_list(conn):
    """applications_by_category returns a list."""
    result = applications_by_category(conn)
    assert isinstance(result, list)


def test_applications_by_category_known_value(conn):
    """applications_by_category includes Product Design with count 3."""
    result = applications_by_category(conn)
    pd = next((r for r in result if r["label"] == "Product Design"), None)
    assert pd is not None
    assert pd["count"] == 3


# ---------------------------------------------------------------------------
# applications_by_work_mode
# ---------------------------------------------------------------------------


def test_applications_by_work_mode_returns_list(conn):
    """applications_by_work_mode returns a list."""
    result = applications_by_work_mode(conn)
    assert isinstance(result, list)


def test_applications_by_work_mode_known_value(conn):
    """applications_by_work_mode includes Onsite with count 3."""
    result = applications_by_work_mode(conn)
    onsite = next((r for r in result if r["label"] == "Onsite"), None)
    assert onsite is not None
    assert onsite["count"] == 3


# ---------------------------------------------------------------------------
# summary_stats
# ---------------------------------------------------------------------------


def test_summary_stats_returns_dict(conn):
    """summary_stats returns a dict."""
    result = summary_stats(conn)
    assert isinstance(result, dict)


def test_summary_stats_total(conn):
    """summary_stats total_applications is 6."""
    result = summary_stats(conn)
    assert result["total_applications"] == 6


def test_summary_stats_active(conn):
    """summary_stats active_applications excludes Rejected/Withdrawn/Ghosted."""
    # Applied×2 + Interview×2 + Offer×1 = 5 active
    result = summary_stats(conn)
    assert result["active_applications"] == 5


def test_summary_stats_response_rate(conn):
    """summary_stats response_rate is 4/6 rounded to 2 dp."""
    result = summary_stats(conn)
    assert result["response_rate"] == round(4 / 6, 2)


def test_summary_stats_avg_priority(conn):
    """summary_stats avg_priority is 3.0 (all rows use the default)."""
    result = summary_stats(conn)
    assert result["avg_priority"] == 3.0
