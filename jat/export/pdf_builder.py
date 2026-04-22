"""PDF document builder for the Job Application Tracker using fpdf2."""

import sqlite3
from datetime import date

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from jat.analytics import queries as analytics_queries

_PAGE_W = 190  # usable width on A4 with 10mm margins each side
_ROW_H = 7
_HEADER_H = 9


def _iso_to_display(date_str: str | None) -> str:
    """Convert YYYY-MM-DD to dd.mm.yyyy, or '---' when None."""
    if not date_str:
        return "---"
    try:
        return date.fromisoformat(date_str).strftime("%d.%m.%Y")
    except ValueError:
        return str(date_str)


def _format_salary_range(currency: str | None, min_val, max_val) -> str:
    """Return a formatted salary range string or '---' when all absent."""
    if currency is None and min_val is None and max_val is None:
        return "---"
    parts: list[str] = []
    if currency:
        parts.append(str(currency))
    if min_val is not None:
        parts.append(str(int(min_val)))
    if min_val is not None and max_val is not None:
        parts.append("--")
    if max_val is not None:
        parts.append(str(int(max_val)))
    return " ".join(parts) if parts else "---"


def _safe(value) -> str:
    """Return str(value) or empty string for None."""
    return str(value) if value is not None else ""


def _new_pdf() -> FPDF:
    """Create a standard A4 PDF with Helvetica font and 10mm margins."""
    pdf = FPDF(format="A4")
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    return pdf


def _write_title(pdf: FPDF, title: str, subtitle: str = "") -> None:
    """Write a bold title and optional subtitle paragraph."""
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        0, 12, title,
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    if subtitle:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(
            0, 8, subtitle,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
    pdf.ln(4)


def _write_filter_line(
    pdf: FPDF,
    date_from: str | None,
    date_to: str | None,
    status_label: str = "",
) -> None:
    """Write a filter summary line below the title."""
    pdf.set_font("Helvetica", "", 9)
    from_str = _iso_to_display(date_from) if date_from else "Alle"
    to_str = _iso_to_display(date_to) if date_to else "Alle"
    line = f"Von: {from_str}   Bis: {to_str}"
    if status_label:
        line += f"   Status: {status_label}"
    pdf.cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)


def build_afa_table(
    conn: sqlite3.Connection,
    output_path: str,
    date_from: str | None = None,
    date_to: str | None = None,
    status_id: int | None = None,
) -> None:
    """Build an AfA table PDF and write it to output_path."""
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

    status_label = "Alle"
    if status_id is not None:
        status_row = conn.execute(
            "SELECT label FROM ref_statuses WHERE id = ?", (status_id,)
        ).fetchone()
        if status_row:
            status_label = _safe(status_row[0])

    pdf = _new_pdf()
    _write_title(pdf, "Bewerbungsliste", f"Gesamt: {len(rows)}")
    _write_filter_line(pdf, date_from, date_to, status_label)

    col_w = [22, 43, 48, 28, 25, 24]
    headers = ["Datum", "Unternehmen", "Stelle", "Quelle", "Status", "Ort"]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(200, 200, 200)
    for w, h in zip(col_w, headers):
        pdf.cell(w, _HEADER_H, h, border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for i, row in enumerate(rows):
        fill = i % 2 == 0
        pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
        cells = [
            _iso_to_display(row[0]),
            _safe(row[1]),
            _safe(row[2]),
            _safe(row[3]),
            _safe(row[4]),
            _safe(row[5]),
        ]
        for w, text in zip(col_w, cells):
            pdf.cell(w, _ROW_H, text[:30], border=1, fill=fill)
        pdf.ln()

    pdf.output(output_path)


def build_application_sheet(
    conn: sqlite3.Connection,
    output_path: str,
    application_id: int,
) -> None:
    """Build an application detail sheet PDF and write it to output_path."""
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

    salary = _format_salary_range(row[11], row[12], row[13])

    pdf = _new_pdf()
    _write_title(pdf, _safe(row[0]), _safe(row[1]))

    label_w = 52
    value_w = _PAGE_W - label_w
    row_h = 8

    fields = [
        ("Bewerbungsdatum", _iso_to_display(row[2])),
        ("Antwortdatum", _iso_to_display(row[3])),
        ("Status", _safe(row[4])),
        ("Kategorie", _safe(row[5])),
        ("Anstellungsart", _safe(row[6])),
        ("Quelle", _safe(row[7])),
        ("Arbeitsmodell", _safe(row[8])),
        ("Stadt", _safe(row[9])),
        ("Land", _safe(row[10])),
        ("Gehalt", salary),
        ("Priorität", _safe(row[14])),
        ("Follow-up", _iso_to_display(row[15])),
        ("Stelle URL", _safe(row[16])),
        ("Notizen", _safe(row[17])),
    ]

    for label, value in fields:
        y_start = pdf.get_y()
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_xy(pdf.l_margin, y_start)
        pdf.cell(label_w, row_h, label + ":", border=0)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_xy(pdf.l_margin + label_w, y_start)
        pdf.multi_cell(value_w, row_h, value, border=0)

    pdf.output(output_path)


def build_analytics_summary(
    conn: sqlite3.Connection,
    output_path: str,
    date_from: str | None = None,
    date_to: str | None = None,
) -> None:
    """Build an analytics summary PDF and write it to output_path."""
    stats = analytics_queries.summary_stats(conn)
    status_rows = analytics_queries.applications_by_status(conn)
    total_for_pct = sum(r["count"] for r in status_rows) or 1

    pdf = _new_pdf()
    _write_title(pdf, "Analytik-Bericht")
    _write_filter_line(pdf, date_from, date_to)

    response_pct = f"{stats['response_rate'] * 100:.0f}%"

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Zusammenfassung", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    summary_fields = [
        ("Bewerbungen gesamt", str(stats["total_applications"])),
        ("Aktive Bewerbungen", str(stats["active_applications"])),
        ("Antwortrate", response_pct),
        ("Durchschn. Priorität", str(stats["avg_priority"])),
    ]

    label_w = 70
    for label, value in summary_fields:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(label_w, 8, label + ":", border=0)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT, border=0)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Status-Verteilung", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    col_w = [80, 30, 30]
    headers = ["Status", "Anzahl", "Anteil"]

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    for w, h in zip(col_w, headers):
        pdf.cell(w, _HEADER_H, h, border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    for i, r in enumerate(status_rows):
        fill = i % 2 == 0
        pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
        pct = f"{r['count'] / total_for_pct * 100:.0f}%"
        for w, text in zip(col_w, [_safe(r["label"]), str(r["count"]), pct]):
            pdf.cell(w, _ROW_H, text, border=1, fill=fill)
        pdf.ln()

    pdf.output(output_path)
