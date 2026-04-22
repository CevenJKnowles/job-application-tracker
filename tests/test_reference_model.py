"""Tests for jat/models/reference.py using an in-memory SQLite database."""

import sqlite3
from unittest.mock import patch

import pytest

import jat.models.reference as ref_model

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REF_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS ref_statuses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    label       TEXT NOT NULL,
    sort_order  INTEGER DEFAULT 0,
    is_active   INTEGER DEFAULT 1
)
"""


def _make_conn():
    """Return a fresh in-memory connection with row_factory set."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(_REF_TABLE_DDL)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TABLE = "ref_statuses"


@pytest.fixture()
def mem_conn(monkeypatch):
    """Patch get_connection so the model uses a shared in-memory database."""
    from contextlib import contextmanager

    conn = _make_conn()

    @contextmanager
    def _fake_get_connection():
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    monkeypatch.setattr(ref_model, "get_connection", _fake_get_connection)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_invalid_table_raises(mem_conn):
    """All public functions reject unrecognised table names."""
    bad = "ref_hackers"
    with pytest.raises(ValueError, match="not a recognised reference table"):
        ref_model.get_all(bad)
    with pytest.raises(ValueError, match="not a recognised reference table"):
        ref_model.get_active(bad)
    with pytest.raises(ValueError, match="not a recognised reference table"):
        ref_model.add_label(bad, "X")
    with pytest.raises(ValueError, match="not a recognised reference table"):
        ref_model.update_label(bad, 1, "X")
    with pytest.raises(ValueError, match="not a recognised reference table"):
        ref_model.set_active(bad, 1, 0)
    with pytest.raises(ValueError, match="not a recognised reference table"):
        ref_model.reorder(bad, [1])


def test_set_active_rejects_invalid_value(mem_conn):
    ref_model.add_label(TABLE, "Applied")
    with pytest.raises(ValueError, match="is_active must be 0 or 1"):
        ref_model.set_active(TABLE, 1, 2)


# ---------------------------------------------------------------------------
# add_label / get_all
# ---------------------------------------------------------------------------


def test_add_label_returns_new_id(mem_conn):
    new_id = ref_model.add_label(TABLE, "Applied")
    assert isinstance(new_id, int)
    assert new_id >= 1


def test_add_multiple_labels_increments_sort_order(mem_conn):
    ref_model.add_label(TABLE, "Applied")
    ref_model.add_label(TABLE, "Interview")
    ref_model.add_label(TABLE, "Offer")

    rows = ref_model.get_all(TABLE)
    assert len(rows) == 3
    orders = [r["sort_order"] for r in rows]
    assert orders == sorted(orders), "sort_order should be monotonically increasing"


def test_get_all_returns_all_rows(mem_conn):
    ref_model.add_label(TABLE, "A")
    ref_model.add_label(TABLE, "B")
    rows = ref_model.get_all(TABLE)
    labels = [r["label"] for r in rows]
    assert "A" in labels and "B" in labels


# ---------------------------------------------------------------------------
# get_active
# ---------------------------------------------------------------------------


def test_get_active_excludes_inactive(mem_conn):
    id_a = ref_model.add_label(TABLE, "Active one")
    id_b = ref_model.add_label(TABLE, "Inactive one")
    ref_model.set_active(TABLE, id_b, 0)

    active = ref_model.get_active(TABLE)
    active_ids = [r["id"] for r in active]
    assert id_a in active_ids
    assert id_b not in active_ids


def test_get_active_returns_only_active(mem_conn):
    ref_model.add_label(TABLE, "Keep")
    id_gone = ref_model.add_label(TABLE, "Gone")
    ref_model.set_active(TABLE, id_gone, 0)

    rows = ref_model.get_active(TABLE)
    assert all(r["is_active"] == 1 for r in rows)


# ---------------------------------------------------------------------------
# update_label
# ---------------------------------------------------------------------------


def test_update_label_changes_text(mem_conn):
    row_id = ref_model.add_label(TABLE, "Old")
    ref_model.update_label(TABLE, row_id, "New")

    rows = ref_model.get_all(TABLE)
    match = next(r for r in rows if r["id"] == row_id)
    assert match["label"] == "New"


# ---------------------------------------------------------------------------
# set_active (deactivate / reactivate)
# ---------------------------------------------------------------------------


def test_deactivate_hides_from_active(mem_conn):
    row_id = ref_model.add_label(TABLE, "Deactivate me")
    ref_model.set_active(TABLE, row_id, 0)

    active = ref_model.get_active(TABLE)
    assert all(r["id"] != row_id for r in active)


def test_reactivate_restores_to_active(mem_conn):
    row_id = ref_model.add_label(TABLE, "Reactivate me")
    ref_model.set_active(TABLE, row_id, 0)
    ref_model.set_active(TABLE, row_id, 1)

    active = ref_model.get_active(TABLE)
    active_ids = [r["id"] for r in active]
    assert row_id in active_ids


def test_set_active_does_not_delete_row(mem_conn):
    row_id = ref_model.add_label(TABLE, "Soft delete check")
    ref_model.set_active(TABLE, row_id, 0)

    all_rows = ref_model.get_all(TABLE)
    assert any(r["id"] == row_id for r in all_rows)


# ---------------------------------------------------------------------------
# reorder
# ---------------------------------------------------------------------------


def test_reorder_updates_sort_order(mem_conn):
    id_a = ref_model.add_label(TABLE, "First")
    id_b = ref_model.add_label(TABLE, "Second")
    id_c = ref_model.add_label(TABLE, "Third")

    # Reverse the order
    ref_model.reorder(TABLE, [id_c, id_b, id_a])

    rows = ref_model.get_all(TABLE)
    order_map = {r["id"]: r["sort_order"] for r in rows}
    assert order_map[id_c] == 0
    assert order_map[id_b] == 1
    assert order_map[id_a] == 2


def test_reorder_reflected_in_get_all_sequence(mem_conn):
    id_a = ref_model.add_label(TABLE, "Alpha")
    id_b = ref_model.add_label(TABLE, "Beta")
    id_c = ref_model.add_label(TABLE, "Gamma")

    ref_model.reorder(TABLE, [id_c, id_a, id_b])

    rows = ref_model.get_all(TABLE)
    ids_in_order = [r["id"] for r in rows]
    assert ids_in_order == [id_c, id_a, id_b]
