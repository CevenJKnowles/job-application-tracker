"""CRUD and query functions for the applications table."""

import sqlite3

from jat.database.connection import get_connection

_UPDATABLE_FIELDS = frozenset(
    {
        "company_id",
        "role_title",
        "application_date",
        "response_date",
        "status_id",
        "category_id",
        "employment_type_id",
        "source_id",
        "job_posting_url",
        "city",
        "country",
        "work_mode_id",
        "salary_min",
        "salary_max",
        "currency_id",
        "priority_score",
        "follow_up_date",
        "notes",
    }
)

_OPTIONAL_INSERT_FIELDS = (
    "status_id",
    "category_id",
    "employment_type_id",
    "source_id",
    "job_posting_url",
    "city",
    "country",
    "work_mode_id",
    "salary_min",
    "salary_max",
    "currency_id",
    "priority_score",
    "follow_up_date",
    "response_date",
    "notes",
)

_SELECT_COLS = (
    "a.*, c.company_name, rs.label AS status_label, "
    "rc.label AS category_label, rw.label AS work_mode_label"
)
_FROM_JOINS = (
    "FROM applications a"
    " LEFT JOIN companies c ON c.company_id = a.company_id"
    " LEFT JOIN ref_statuses rs ON rs.id = a.status_id"
    " LEFT JOIN ref_categories rc ON rc.id = a.category_id"
    " LEFT JOIN ref_work_modes rw ON rw.id = a.work_mode_id"
)


def add_application(
    company_id: int,
    role_title: str,
    application_date: str,
    **kwargs,
) -> int:
    """Insert a new application row and return its new application_id."""
    columns = ["company_id", "role_title", "application_date"]
    values: list = [company_id, role_title, application_date]

    for field in _OPTIONAL_INSERT_FIELDS:
        if field in kwargs:
            columns.append(field)
            values.append(kwargs[field])

    placeholders = ", ".join("?" * len(columns))
    col_list = ", ".join(columns)
    with get_connection() as conn:
        cursor = conn.execute(
            f"INSERT INTO applications ({col_list}) VALUES ({placeholders})",
            values,
        )
    return cursor.lastrowid


def get_application_by_id(application_id: int) -> sqlite3.Row | None:
    """Return a single application row by primary key, or None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE application_id = ?",
            (application_id,),
        ).fetchone()
    return row


def get_all_applications() -> list[sqlite3.Row]:
    """Return all applications joined to companies and ref tables, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {_SELECT_COLS} {_FROM_JOINS} ORDER BY a.application_date DESC"
        ).fetchall()
    return rows


def update_application(application_id: int, **kwargs) -> None:
    """Update only the supplied fields; always refreshes updated_at."""
    if not kwargs:
        raise ValueError("At least one field must be supplied to update.")

    valid = {k: v for k, v in kwargs.items() if k in _UPDATABLE_FIELDS}
    if not valid:
        raise ValueError("No valid fields supplied to update.")

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM applications WHERE application_id = ?",
            (application_id,),
        ).fetchone()
        if existing is None:
            raise ValueError(
                f"Application with id {application_id} does not exist."
            )
        set_clause = ", ".join(f"{col} = ?" for col in valid)
        set_clause += ", updated_at = datetime('now', 'localtime')"
        conn.execute(
            f"UPDATE applications SET {set_clause} WHERE application_id = ?",
            [*valid.values(), application_id],
        )


def delete_application(application_id: int) -> None:
    """Delete an application row by primary key; raises ValueError if not found."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM applications WHERE application_id = ?",
            (application_id,),
        ).fetchone()
        if existing is None:
            raise ValueError(
                f"Application with id {application_id} does not exist."
            )
        conn.execute(
            "DELETE FROM applications WHERE application_id = ?",
            (application_id,),
        )


def search_applications(query: str) -> list[sqlite3.Row]:
    """Return applications whose role_title or notes match query (case-insensitive)."""
    pattern = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {_SELECT_COLS} {_FROM_JOINS}"
            " WHERE LOWER(a.role_title) LIKE LOWER(?)"
            " OR LOWER(a.notes) LIKE LOWER(?)"
            " ORDER BY a.application_date DESC",
            (pattern, pattern),
        ).fetchall()
    return rows


def filter_applications(
    status_id: int | None = None,
    category_id: int | None = None,
    company_id: int | None = None,
) -> list[sqlite3.Row]:
    """Return applications matching the supplied filters; at least one required."""
    conditions = []
    params = []
    if status_id is not None:
        conditions.append("a.status_id = ?")
        params.append(status_id)
    if category_id is not None:
        conditions.append("a.category_id = ?")
        params.append(category_id)
    if company_id is not None:
        conditions.append("a.company_id = ?")
        params.append(company_id)

    if not conditions:
        raise ValueError("At least one filter must be supplied.")

    where = " AND ".join(conditions)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {_SELECT_COLS} {_FROM_JOINS}"
            f" WHERE {where}"
            " ORDER BY a.application_date DESC",
            params,
        ).fetchall()
    return rows
