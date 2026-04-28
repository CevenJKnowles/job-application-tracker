"""CRUD and query functions for the companies table."""

import sqlite3

from jat.database.connection import get_connection

_SELECT_COLUMNS = """
    c.company_id    AS id,
    c.company_name,
    c.industry,
    c.company_website AS website,
    c.notes,
    c.contact_name,
    c.contact_email,
    c.contact_phone_prefix,
    c.contact_phone_number,
    c.created_at,
    COUNT(a.application_id) AS application_count
"""

_FROM_JOIN = """
FROM companies c
LEFT JOIN applications a ON a.company_id = c.company_id
"""


def get_all_companies() -> list[sqlite3.Row]:
    """Return all companies ordered by name with a computed application_count."""
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {_SELECT_COLUMNS} {_FROM_JOIN} GROUP BY c.company_id"
            " ORDER BY c.company_name ASC"
        ).fetchall()
    return rows


def get_company_by_id(company_id: int) -> sqlite3.Row | None:
    """Return a single company row by primary key, or None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT {_SELECT_COLUMNS} {_FROM_JOIN}"
            " WHERE c.company_id = ? GROUP BY c.company_id",
            (company_id,),
        ).fetchone()
    return row


def add_company(
    company_name: str,
    industry: str = "",
    website: str = "",
    notes: str = "",
    contact_name: str = "",
    contact_email: str = "",
    contact_phone_prefix: str = "",
    contact_phone_number: str = "",
) -> int:
    """Insert a new company row and return its new id.

    Raises ValueError if a company with the same name already exists
    (case-insensitive).
    """
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM companies WHERE LOWER(company_name) = LOWER(?)",
            (company_name,),
        ).fetchone()
        if existing:
            raise ValueError("Company name already exists.")
        cursor = conn.execute(
            "INSERT INTO companies"
            " (company_name, industry, company_website, notes,"
            "  contact_name, contact_email, contact_phone_prefix, contact_phone_number)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                company_name,
                industry,
                website,
                notes,
                contact_name,
                contact_email,
                contact_phone_prefix,
                contact_phone_number,
            ),
        )
    return cursor.lastrowid


def update_company(
    company_id: int,
    company_name: str,
    industry: str = "",
    website: str = "",
    notes: str = "",
    contact_name: str = "",
    contact_email: str = "",
    contact_phone_prefix: str = "",
    contact_phone_number: str = "",
) -> None:
    """Update an existing company row.

    Raises ValueError if company_name conflicts with any other company
    (case-insensitive, excluding the current row).
    """
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM companies"
            " WHERE LOWER(company_name) = LOWER(?) AND company_id != ?",
            (company_name, company_id),
        ).fetchone()
        if existing:
            raise ValueError("Company name already exists.")
        conn.execute(
            "UPDATE companies"
            " SET company_name = ?, industry = ?, company_website = ?, notes = ?,"
            "     contact_name = ?, contact_email = ?,"
            "     contact_phone_prefix = ?, contact_phone_number = ?"
            " WHERE company_id = ?",
            (
                company_name,
                industry,
                website,
                notes,
                contact_name,
                contact_email,
                contact_phone_prefix,
                contact_phone_number,
                company_id,
            ),
        )


def delete_company(company_id: int) -> None:
    """Delete a company row.

    Raises ValueError if any applications are linked to this company.
    """
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE company_id = ?",
            (company_id,),
        ).fetchone()[0]
        if count > 0:
            raise ValueError("Cannot delete a company with linked applications.")
        conn.execute(
            "DELETE FROM companies WHERE company_id = ?",
            (company_id,),
        )


def search_companies(query: str) -> list[sqlite3.Row]:
    """Return companies whose name or industry matches query (case-insensitive LIKE)."""
    pattern = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {_SELECT_COLUMNS} {_FROM_JOIN}"
            " WHERE LOWER(c.company_name) LIKE LOWER(?)"
            " OR LOWER(c.industry) LIKE LOWER(?)"
            " GROUP BY c.company_id"
            " ORDER BY c.company_name ASC",
            (pattern, pattern),
        ).fetchall()
    return rows


def get_company_application_count(company_id: int) -> int:
    """Return the number of applications linked to this company."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE company_id = ?",
            (company_id,),
        ).fetchone()
    return row[0]


def get_company_links(company_id: int) -> list[dict]:
    """Return all links for a company ordered by link_id."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT link_id, platform, url FROM company_links"
            " WHERE company_id = ? ORDER BY link_id ASC",
            (company_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def add_company_link(company_id: int, platform: str, url: str) -> int:
    """Insert a link for a company and return the new link_id."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO company_links (company_id, platform, url) VALUES (?, ?, ?)",
            (company_id, platform, url),
        )
    return cursor.lastrowid


def delete_company_link(link_id: int) -> None:
    """Delete a company link by link_id."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM company_links WHERE link_id = ?",
            (link_id,),
        )


def get_all_industries() -> list[str]:
    """Return distinct non-empty industry values ordered alphabetically."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT industry FROM companies"
            " WHERE industry IS NOT NULL AND industry != ''"
            " ORDER BY industry ASC"
        ).fetchall()
    return [row[0] for row in rows]
