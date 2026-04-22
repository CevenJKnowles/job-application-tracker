"""Analytics SQL queries for the Job Application Tracker."""

import sqlite3


def applications_by_status(conn: sqlite3.Connection) -> list[dict]:
    """Return application counts grouped by status label, ordered by count descending."""
    rows = conn.execute(
        """
        SELECT rs.label, COUNT(a.application_id) AS count
        FROM applications a
        JOIN ref_statuses rs ON a.status_id = rs.id
        WHERE a.status_id IS NOT NULL
        GROUP BY rs.id
        ORDER BY count DESC
        """
    ).fetchall()
    return [{"label": row[0], "count": row[1]} for row in rows]


def applications_over_time(conn: sqlite3.Connection) -> list[dict]:
    """Return application counts grouped by year-month, ordered chronologically."""
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', application_date) AS period,
               COUNT(application_id) AS count
        FROM applications
        GROUP BY period
        ORDER BY period ASC
        """
    ).fetchall()
    return [{"period": row[0], "count": row[1]} for row in rows]


def applications_by_category(conn: sqlite3.Connection) -> list[dict]:
    """Return application counts grouped by category label, ordered by count descending."""
    rows = conn.execute(
        """
        SELECT rc.label, COUNT(a.application_id) AS count
        FROM applications a
        JOIN ref_categories rc ON a.category_id = rc.id
        WHERE a.category_id IS NOT NULL
        GROUP BY rc.id
        ORDER BY count DESC
        """
    ).fetchall()
    return [{"label": row[0], "count": row[1]} for row in rows]


def applications_by_work_mode(conn: sqlite3.Connection) -> list[dict]:
    """Return application counts grouped by work mode label, ordered by count descending."""
    rows = conn.execute(
        """
        SELECT rw.label, COUNT(a.application_id) AS count
        FROM applications a
        JOIN ref_work_modes rw ON a.work_mode_id = rw.id
        WHERE a.work_mode_id IS NOT NULL
        GROUP BY rw.id
        ORDER BY count DESC
        """
    ).fetchall()
    return [{"label": row[0], "count": row[1]} for row in rows]


def summary_stats(conn: sqlite3.Connection) -> dict:
    """Return high-level summary statistics across all applications."""
    total_row = conn.execute(
        "SELECT COUNT(application_id) FROM applications"
    ).fetchone()
    total = total_row[0]

    active_row = conn.execute(
        """
        SELECT COUNT(a.application_id)
        FROM applications a
        JOIN ref_statuses rs ON a.status_id = rs.id
        WHERE rs.label NOT IN ('Rejected', 'Withdrawn', 'Ghosted')
        """
    ).fetchone()
    active = active_row[0]

    responded_row = conn.execute(
        "SELECT COUNT(application_id) FROM applications WHERE response_date IS NOT NULL"
    ).fetchone()
    responded = responded_row[0]
    response_rate = round(responded / total, 2) if total > 0 else 0.0

    avg_row = conn.execute(
        "SELECT AVG(priority_score) FROM applications"
    ).fetchone()
    avg_priority = round(avg_row[0], 2) if avg_row[0] is not None else 0.0

    return {
        "total_applications": total,
        "active_applications": active,
        "response_rate": response_rate,
        "avg_priority": avg_priority,
    }
