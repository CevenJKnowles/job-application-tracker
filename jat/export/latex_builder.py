"""LaTeX document builder for the Job Application Tracker."""

import sqlite3
from datetime import date
from pathlib import Path

from jat.analytics import queries as analytics_queries

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_LATEX_ESCAPE_MAP: dict[str, str] = {
    "\\": "\\textbackslash{}",
    "&": "\\&",
    "%": "\\%",
    "$": "\\$",
    "#": "\\#",
    "_": "\\_",
    "{": "\\{",
    "}": "\\}",
    "~": "\\textasciitilde{}",
    "^": "\\textasciicircum{}",
}


def escape_latex(text) -> str:
    """Escape LaTeX special characters; returns '---' for None, '' unchanged."""
    if text is None:
        return "---"
    text = str(text)
    if text == "":
        return ""
    return "".join(_LATEX_ESCAPE_MAP.get(ch, ch) for ch in text)


def load_template(template_name: str) -> str:
    """Read and return the named template from jat/export/templates/."""
    path = _TEMPLATES_DIR / template_name
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def write_file(content: str, output_path: str) -> None:
    """Write UTF-8 text to output_path; raises IOError on failure."""
    try:
        Path(output_path).write_text(content, encoding="utf-8")
    except OSError as exc:
        raise IOError(f"Could not write to {output_path}: {exc}") from exc


def _iso_to_display(date_str: str | None) -> str:
    """Convert YYYY-MM-DD to dd.mm.yyyy, or 'Alle' when None."""
    if not date_str:
        return "Alle"
    try:
        return date.fromisoformat(date_str).strftime("%d.%m.%Y")
    except ValueError:
        return date_str


def _format_salary_range(
    currency: str | None, min_val, max_val
) -> str:
    """Return a formatted salary range string or '---' when all absent."""
    if currency is None and min_val is None and max_val is None:
        return "---"
    parts: list[str] = []
    if currency:
        parts.append(currency)
    if min_val is not None:
        parts.append(str(int(min_val)))
    if min_val is not None and max_val is not None:
        parts.append("--")
    if max_val is not None:
        parts.append(str(int(max_val)))
    return " ".join(parts) if parts else "---"


def build_afa_table(
    conn: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    status_id: int | None = None,
) -> str:
    """Build and return a rendered afa_table.tex string."""
    conditions: list[str] = []
    params: list = []
    if date_from:
        conditions.append("a.application_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("a.application_date <= ?")
        params.append(date_to)
    if status_id is not None:
        conditions.append("a.status_id = ?")
        params.append(status_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    rows = conn.execute(
        f"""
        SELECT a.application_date, c.company_name, a.role_title,
               rsrc.label AS source_label, rs.label AS status_label, a.city
        FROM applications a
        LEFT JOIN companies c ON c.company_id = a.company_id
        LEFT JOIN ref_statuses rs ON rs.id = a.status_id
        LEFT JOIN ref_sources rsrc ON rsrc.id = a.source_id
        {where}
        ORDER BY a.application_date DESC
        """,
        params,
    ).fetchall()

    row_lines: list[str] = []
    for row in rows:
        col_date = escape_latex(_iso_to_display(row[0]))
        col_company = escape_latex(row[1])
        col_role = escape_latex(row[2])
        col_source = escape_latex(row[3])
        col_status = escape_latex(row[4])
        col_city = escape_latex(row[5])
        row_lines.append(
            f"{col_date} & {col_company} & {col_role} & "
            f"{col_source} & {col_status} & {col_city} \\\\"
        )

    status_label = "Alle"
    if status_id is not None:
        status_row = conn.execute(
            "SELECT label FROM ref_statuses WHERE id = ?", (status_id,)
        ).fetchone()
        if status_row:
            status_label = escape_latex(status_row[0])

    template = load_template("afa_table.tex")
    today = date.today().strftime("%d.%m.%Y")

    return (
        template
        .replace("<<EXPORT_DATE>>", today)
        .replace("<<DATE_FROM>>", _iso_to_display(date_from))
        .replace("<<DATE_TO>>", _iso_to_display(date_to))
        .replace("<<STATUS_FILTER>>", status_label)
        .replace("<<TOTAL_COUNT>>", str(len(rows)))
        .replace("<<TABLE_ROWS>>", "\n".join(row_lines))
    )


def build_application_sheet(
    conn: sqlite3.Connection,
    application_id: int,
) -> str:
    """Build and return a rendered application_sheet.tex string."""
    row = conn.execute(
        """
        SELECT
            a.role_title, c.company_name, a.application_date,
            a.response_date, rs.label AS status_label,
            rc.label AS category_label,
            ret.label AS employment_type_label,
            rsrc.label AS source_label,
            rw.label AS work_mode_label,
            a.city, a.country, rcur.label AS currency_label,
            a.salary_min, a.salary_max,
            a.priority_score, a.follow_up_date,
            a.job_posting_url, a.notes
        FROM applications a
        LEFT JOIN companies c ON c.company_id = a.company_id
        LEFT JOIN ref_statuses rs ON rs.id = a.status_id
        LEFT JOIN ref_categories rc ON rc.id = a.category_id
        LEFT JOIN ref_employment_types ret ON ret.id = a.employment_type_id
        LEFT JOIN ref_sources rsrc ON rsrc.id = a.source_id
        LEFT JOIN ref_work_modes rw ON rw.id = a.work_mode_id
        LEFT JOIN ref_currencies rcur ON rcur.id = a.currency_id
        WHERE a.application_id = ?
        """,
        (application_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"Application {application_id} not found.")

    notes_clean = (row[17] or "").replace("\n", " ").replace("\r", " ")

    salary = _format_salary_range(row[11], row[12], row[13])

    url_raw = row[16]
    if url_raw:
        job_url = "\\texttt{" + escape_latex(url_raw) + "}"
    else:
        job_url = "---"

    template = load_template("application_sheet.tex")
    return (
        template
        .replace("<<ROLE_TITLE>>", escape_latex(row[0]))
        .replace("<<COMPANY_NAME>>", escape_latex(row[1]))
        .replace("<<APPLICATION_DATE>>", escape_latex(_iso_to_display(row[2])))
        .replace("<<RESPONSE_DATE>>", escape_latex(_iso_to_display(row[3])))
        .replace("<<STATUS>>", escape_latex(row[4]))
        .replace("<<CATEGORY>>", escape_latex(row[5]))
        .replace("<<EMPLOYMENT_TYPE>>", escape_latex(row[6]))
        .replace("<<SOURCE>>", escape_latex(row[7]))
        .replace("<<WORK_MODE>>", escape_latex(row[8]))
        .replace("<<CITY>>", escape_latex(row[9]))
        .replace("<<COUNTRY>>", escape_latex(row[10]))
        .replace("<<SALARY_RANGE>>", escape_latex(salary))
        .replace("<<PRIORITY>>", escape_latex(row[14]))
        .replace("<<FOLLOW_UP_DATE>>", escape_latex(_iso_to_display(row[15])))
        .replace("<<JOB_URL>>", job_url)
        .replace("<<NOTES>>", escape_latex(notes_clean))
    )


def build_analytics_summary(
    conn: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """Build and return a rendered analytics_summary.tex string."""
    stats = analytics_queries.summary_stats(conn)
    status_rows = analytics_queries.applications_by_status(conn)

    total_for_pct = sum(r["count"] for r in status_rows) or 1

    status_lines: list[str] = []
    for r in status_rows:
        pct = f"{r['count'] / total_for_pct * 100:.0f}\\%"
        status_lines.append(
            f"{escape_latex(r['label'])} & {r['count']} & {pct} \\\\"
        )

    response_rate_str = f"{stats['response_rate'] * 100:.0f}\\%"
    avg_priority_str = str(stats["avg_priority"])

    template = load_template("analytics_summary.tex")
    today = date.today().strftime("%d.%m.%Y")

    return (
        template
        .replace("<<EXPORT_DATE>>", today)
        .replace("<<DATE_FROM>>", _iso_to_display(date_from))
        .replace("<<DATE_TO>>", _iso_to_display(date_to))
        .replace("<<TOTAL_APPLICATIONS>>", str(stats["total_applications"]))
        .replace("<<ACTIVE_APPLICATIONS>>", str(stats["active_applications"]))
        .replace("<<RESPONSE_RATE>>", response_rate_str)
        .replace("<<AVG_PRIORITY>>", avg_priority_str)
        .replace("<<STATUS_TABLE_ROWS>>", "\n".join(status_lines))
    )
