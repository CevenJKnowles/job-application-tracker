"""Generic CRUD model for all ref_ reference tables."""

from typing import Any

from jat.database.connection import get_connection

ALLOWED_TABLES = frozenset(
    {
        "ref_statuses",
        "ref_categories",
        "ref_employment_types",
        "ref_sources",
        "ref_work_modes",
        "ref_currencies",
    }
)


def _validate(table_name: str) -> None:
    """Raise ValueError if table_name is not in ALLOWED_TABLES."""
    if table_name not in ALLOWED_TABLES:
        raise ValueError(
            f"'{table_name}' is not a recognised reference table. "
            f"Allowed: {sorted(ALLOWED_TABLES)}"
        )


def get_all(table_name: str) -> list[dict[str, Any]]:
    """Return all rows from table_name ordered by sort_order."""
    _validate(table_name)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table_name} ORDER BY sort_order, id"
        ).fetchall()
    return [dict(row) for row in rows]


def get_active(table_name: str) -> list[dict[str, Any]]:
    """Return only is_active = 1 rows from table_name ordered by sort_order."""
    _validate(table_name)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table_name} WHERE is_active = 1 ORDER BY sort_order, id"
        ).fetchall()
    return [dict(row) for row in rows]


def add_label(table_name: str, label: str) -> int:
    """Insert a new row with label and sort_order = max(sort_order) + 1. Return new id."""
    _validate(table_name)
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT COALESCE(MAX(sort_order), -1) AS max_order FROM {table_name}"
        ).fetchone()
        next_order = row["max_order"] + 1
        cursor = conn.execute(
            f"INSERT INTO {table_name} (label, sort_order) VALUES (?, ?)",
            (label, next_order),
        )
    return cursor.lastrowid


def update_label(table_name: str, row_id: int, new_label: str) -> None:
    """Update the label of the row with the given id."""
    _validate(table_name)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE {table_name} SET label = ? WHERE id = ?",
            (new_label, row_id),
        )


def set_active(table_name: str, row_id: int, is_active: int) -> None:
    """Set is_active to 0 or 1 for the row with the given id. Never deletes."""
    _validate(table_name)
    if is_active not in (0, 1):
        raise ValueError("is_active must be 0 or 1.")
    with get_connection() as conn:
        conn.execute(
            f"UPDATE {table_name} SET is_active = ? WHERE id = ?",
            (is_active, row_id),
        )


def reorder(table_name: str, ordered_ids: list[int]) -> None:
    """Set sort_order of each id to its position index in ordered_ids."""
    _validate(table_name)
    with get_connection() as conn:
        for position, row_id in enumerate(ordered_ids):
            conn.execute(
                f"UPDATE {table_name} SET sort_order = ? WHERE id = ?",
                (position, row_id),
            )


def set_funnel_order(row_id: int, value: int | None) -> None:
    """Set funnel_order for the ref_statuses row with the given id. value=None clears it."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE ref_statuses SET funnel_order = ? WHERE id = ?",
            (value, row_id),
        )
