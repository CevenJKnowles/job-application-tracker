"""Database schema creation for the Job Application Tracker."""

from jat.database.connection import get_connection

_DDL = [
    # ref_phases before applications (applications.phase_id references it)
    """
    CREATE TABLE IF NOT EXISTS ref_phases (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        label       TEXT NOT NULL,
        sort_order  INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1
    )
    """,
    # Reference tables must come before applications (foreign key targets)
    """
    CREATE TABLE IF NOT EXISTS ref_statuses (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        label       TEXT NOT NULL,
        sort_order  INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1,
        funnel_order INTEGER
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
        notes               TEXT,
        industry            TEXT,
        company_size_band   TEXT,
        linkedin_url        TEXT,
        contact_name        TEXT,
        contact_email       TEXT,
        contact_phone_prefix TEXT,
        contact_phone_number TEXT,
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
        phase_id            INTEGER REFERENCES ref_phases(id),
        created_at          DATETIME DEFAULT (datetime('now', 'localtime')),
        updated_at          DATETIME DEFAULT (datetime('now', 'localtime'))
    )
    """,
    # company_links after companies (references companies)
    """
    CREATE TABLE IF NOT EXISTS company_links (
        link_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id  INTEGER NOT NULL REFERENCES companies(company_id),
        platform    TEXT NOT NULL,
        url         TEXT NOT NULL
    )
    """,
]

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_applications_company_id"
    "      ON applications(company_id)",
    "CREATE INDEX IF NOT EXISTS idx_applications_status_id"
    "       ON applications(status_id)",
    "CREATE INDEX IF NOT EXISTS idx_applications_application_date"
    " ON applications(application_date)",
    "CREATE INDEX IF NOT EXISTS idx_companies_company_name"
    "       ON companies(company_name)",
    "CREATE INDEX IF NOT EXISTS idx_company_links_company_id"
    "  ON company_links(company_id)",
]

# All columns in insertion order, used by the priority_score migration.
_APPLICATIONS_COPY_COLUMNS = (
    "application_id, company_id, role_title, application_date, response_date, "
    "status_id, category_id, employment_type_id, source_id, job_posting_url, "
    "city, country, work_mode_id, salary_min, salary_max, currency_id, "
    "priority_score, follow_up_date, notes, created_at, updated_at"
)


def _has_priority_check(conn) -> bool:
    """Return True if the applications table already has the priority_score CHECK."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'applications'"
    ).fetchone()
    return row is not None and "CHECK(priority_score" in row["sql"]


def _migrate_add_priority_check(conn) -> None:
    """Rebuild the applications table to add CHECK(priority_score BETWEEN 1 AND 5).

    SQLite does not support ALTER COLUMN, so the standard rename-create-copy-drop
    pattern is used.
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


def _seed_ref_phases(conn) -> None:
    """Insert the five default phase rows (only called when ref_phases is empty)."""
    phases = [
        ("Applied", 1),
        ("Interview #1", 2),
        ("Interview #2", 3),
        ("Interview #3", 4),
        ("Final Stage", 5),
    ]
    conn.executemany(
        "INSERT INTO ref_phases (label, sort_order) VALUES (?, ?)",
        phases,
    )


def _migrate_statuses_to_phases(conn) -> None:
    """Move Applied/Interview/Final Stage status rows to phase_id; soft-delete them."""
    mapping = [
        ("Applied", "Applied"),
        ("Interview", "Interview #1"),
        ("Final Stage", "Final Stage"),
    ]
    for status_label, phase_label in mapping:
        status_row = conn.execute(
            "SELECT id FROM ref_statuses WHERE label = ?", (status_label,)
        ).fetchone()
        phase_row = conn.execute(
            "SELECT id FROM ref_phases WHERE label = ?", (phase_label,)
        ).fetchone()
        if status_row and phase_row:
            conn.execute(
                "UPDATE applications SET phase_id = ?, status_id = NULL"
                " WHERE status_id = ?",
                (phase_row["id"], status_row["id"]),
            )

    for label in ("Applied", "Interview", "Final Stage"):
        conn.execute(
            "UPDATE ref_statuses SET is_active = 0 WHERE label = ?",
            (label,),
        )


def run_migrations(conn) -> None:
    """Apply all schema changes needed on existing databases. Safe on every startup."""
    # ── Existing Phase 1 migrations ──────────────────────────────────────────
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(companies)")}
    if "notes" not in columns:
        conn.execute("ALTER TABLE companies ADD COLUMN notes TEXT")

    status_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(ref_statuses)")
    }
    if "funnel_order" not in status_columns:
        conn.execute("ALTER TABLE ref_statuses ADD COLUMN funnel_order INTEGER")

    for label, order in (
        ("Applied", 1),
        ("Interview", 2),
        ("Final Stage", 3),
        ("Offer", 4),
    ):
        conn.execute(
            "UPDATE ref_statuses SET funnel_order = ?"
            " WHERE funnel_order IS NULL AND label = ?",
            (order, label),
        )

    # ── Phase 2 column migrations ─────────────────────────────────────────────
    app_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(applications)")
    }
    if "phase_id" not in app_columns:
        conn.execute(
            "ALTER TABLE applications"
            " ADD COLUMN phase_id INTEGER REFERENCES ref_phases(id)"
        )

    # Re-read companies columns in case the table was just created with new cols
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(companies)")}
    if "contact_name" not in columns:
        conn.execute("ALTER TABLE companies ADD COLUMN contact_name TEXT")
    if "contact_email" not in columns:
        conn.execute("ALTER TABLE companies ADD COLUMN contact_email TEXT")
    if "contact_phone_prefix" not in columns:
        conn.execute("ALTER TABLE companies ADD COLUMN contact_phone_prefix TEXT")
    if "contact_phone_number" not in columns:
        conn.execute("ALTER TABLE companies ADD COLUMN contact_phone_number TEXT")

    # ── Phase 2 data migration (guard: only when ref_phases is empty) ─────────
    phase_count = conn.execute("SELECT COUNT(*) FROM ref_phases").fetchone()[0]
    if phase_count == 0:
        _seed_ref_phases(conn)
        _migrate_statuses_to_phases(conn)


def create_tables() -> None:
    """Create all tables and indexes. Safe to call on an already-initialised database."""
    with get_connection() as conn:
        for statement in _DDL:
            conn.execute(statement)
        if not _has_priority_check(conn):
            _migrate_add_priority_check(conn)
        for statement in _INDEXES:
            conn.execute(statement)


if __name__ == "__main__":
    create_tables()
