"""Database schema creation for the Job Application Tracker."""

from jat.database.connection import get_connection

_DDL = [
    # Reference tables must come before applications (foreign key targets)
    """
    CREATE TABLE IF NOT EXISTS ref_statuses (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        label       TEXT NOT NULL,
        sort_order  INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ref_categories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        label       TEXT NOT NULL,
        sort_order  INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ref_employment_types (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        label       TEXT NOT NULL,
        sort_order  INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ref_sources (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        label       TEXT NOT NULL,
        sort_order  INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ref_work_modes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        label       TEXT NOT NULL,
        sort_order  INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ref_currencies (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        label       TEXT NOT NULL,
        sort_order  INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS companies (
        company_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name        TEXT NOT NULL UNIQUE,
        company_website     TEXT,
        industry            TEXT,
        company_size_band   TEXT,
        linkedin_url        TEXT,
        created_at          DATETIME DEFAULT (datetime('now', 'localtime'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS applications (
        application_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id          INTEGER NOT NULL REFERENCES companies(company_id),
        role_title          TEXT NOT NULL,
        application_date    DATE NOT NULL,
        response_date       DATE,
        status_id           INTEGER REFERENCES ref_statuses(id),
        category_id         INTEGER REFERENCES ref_categories(id),
        employment_type_id  INTEGER REFERENCES ref_employment_types(id),
        source_id           INTEGER REFERENCES ref_sources(id),
        job_posting_url     TEXT,
        city                TEXT,
        country             TEXT,
        work_mode_id        INTEGER REFERENCES ref_work_modes(id),
        salary_min          REAL,
        salary_max          REAL,
        currency_id         INTEGER REFERENCES ref_currencies(id),
        priority_score      INTEGER DEFAULT 3 CHECK(priority_score BETWEEN 1 AND 5),
        follow_up_date      DATE,
        notes               TEXT,
        created_at          DATETIME DEFAULT (datetime('now', 'localtime')),
        updated_at          DATETIME DEFAULT (datetime('now', 'localtime'))
    )
    """,
]

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_applications_company_id      ON applications(company_id)",
    "CREATE INDEX IF NOT EXISTS idx_applications_status_id       ON applications(status_id)",
    "CREATE INDEX IF NOT EXISTS idx_applications_application_date ON applications(application_date)",
    "CREATE INDEX IF NOT EXISTS idx_companies_company_name       ON companies(company_name)",
]

# All columns in insertion order, used by the priority_score migration.
_APPLICATIONS_COPY_COLUMNS = (
    "application_id, company_id, role_title, application_date, response_date, "
    "status_id, category_id, employment_type_id, source_id, job_posting_url, "
    "city, country, work_mode_id, salary_min, salary_max, currency_id, "
    "priority_score, follow_up_date, notes, created_at, updated_at"
)


def _has_priority_check(conn) -> bool:
    """Return True if the applications table already has the priority_score CHECK constraint."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'applications'"
    ).fetchone()
    return row is not None and "CHECK(priority_score" in row["sql"]


def _migrate_add_priority_check(conn) -> None:
    """Rebuild the applications table to add CHECK(priority_score BETWEEN 1 AND 5).

    SQLite does not support ALTER COLUMN, so the standard rename-create-copy-drop
    pattern is used. Foreign key enforcement is temporarily disabled for the
    duration of the rebuild and re-enabled (with a check) before returning.
    """
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("ALTER TABLE applications RENAME TO applications_old")
    conn.execute(
        """
        CREATE TABLE applications (
            application_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id          INTEGER NOT NULL REFERENCES companies(company_id),
            role_title          TEXT NOT NULL,
            application_date    DATE NOT NULL,
            response_date       DATE,
            status_id           INTEGER REFERENCES ref_statuses(id),
            category_id         INTEGER REFERENCES ref_categories(id),
            employment_type_id  INTEGER REFERENCES ref_employment_types(id),
            source_id           INTEGER REFERENCES ref_sources(id),
            job_posting_url     TEXT,
            city                TEXT,
            country             TEXT,
            work_mode_id        INTEGER REFERENCES ref_work_modes(id),
            salary_min          REAL,
            salary_max          REAL,
            currency_id         INTEGER REFERENCES ref_currencies(id),
            priority_score      INTEGER DEFAULT 3 CHECK(priority_score BETWEEN 1 AND 5),
            follow_up_date      DATE,
            notes               TEXT,
            created_at          DATETIME DEFAULT (datetime('now', 'localtime')),
            updated_at          DATETIME DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conn.execute(
        f"INSERT INTO applications SELECT {_APPLICATIONS_COPY_COLUMNS}"
        " FROM applications_old"
    )
    conn.execute("DROP TABLE applications_old")
    conn.execute("PRAGMA foreign_key_check")
    conn.execute("PRAGMA foreign_keys = ON")


def create_tables() -> None:
    """Create all tables and indexes. Safe to call on an already-initialised database."""
    with get_connection() as conn:
        for statement in _DDL:
            conn.execute(statement)
        if not _has_priority_check(conn):
            _migrate_add_priority_check(conn)
        # Indexes run after any migration: the rebuild drops indexes on the old table.
        for statement in _INDEXES:
            conn.execute(statement)


if __name__ == "__main__":
    create_tables()
    print("Schema created.")
