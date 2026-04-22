"""Default reference data seeding for the Job Application Tracker database."""

from jat.database.connection import get_connection

_SEEDS = {
    "ref_statuses": [
        "Applied",
        "Reviewing",
        "Interview",
        "Final Stage",
        "Offer",
        "Rejected",
        "Withdrawn",
        "Ghosted",
    ],
    "ref_categories": [
        "Product Design",
        "UX/UI Design",
        "Service Design",
        "Creative Direction",
        "AI Strategy",
        "Prompt Engineering",
        "Innovation",
        "Research",
        "Marketing",
        "Operations",
    ],
    "ref_employment_types": [
        "Full-time",
        "Part-time",
        "Contract",
        "Freelance",
        "Internship",
        "Temporary",
    ],
    "ref_sources": [
        "LinkedIn",
        "Company Website",
        "Referral",
        "Recruiter Outreach",
        "Indeed",
        "Glassdoor",
        "Networking",
        "Other",
    ],
    "ref_work_modes": [
        "Onsite",
        "Hybrid",
        "Remote",
    ],
    "ref_currencies": [
        "EUR",
        "GBP",
        "USD",
        "CHF",
    ],
}


def _table_is_empty(conn, table: str) -> bool:
    """Return True if the given table contains no rows."""
    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return row[0] == 0


def seed_defaults() -> None:
    """Insert default reference values into all ref_ tables.

    Uses INSERT OR IGNORE so existing rows are never duplicated. Each table is
    only seeded when it is empty, matching the documented behaviour in CLAUDE.md.
    """
    with get_connection() as conn:
        for table, labels in _SEEDS.items():
            if not _table_is_empty(conn, table):
                continue
            rows = [(label, idx) for idx, label in enumerate(labels)]
            conn.executemany(
                f"INSERT OR IGNORE INTO {table} (label, sort_order) VALUES (?, ?)",
                rows,
            )


if __name__ == "__main__":
    seed_defaults()
    print("Reference data seeded.")
