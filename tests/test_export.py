"""Tests for jat/export/ builders using an in-memory SQLite database."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

import jat.database.schema as schema_mod
import jat.database.seed as seed_mod
from jat.export.latex_builder import (
    escape_latex,
    build_afa_table,
    build_application_sheet,
    build_analytics_summary,
    write_file,
)
import jat.export.pdf_builder as pdf_builder
import jat.export.docx_builder as docx_builder
import jat.export.odt_builder as odt_builder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_in_memory_db(monkeypatch):
    """Create an in-memory SQLite DB with schema, migrations, and seeds applied."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    @contextmanager
    def _fake_get_connection():
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    monkeypatch.setattr(schema_mod, "get_connection", _fake_get_connection)
    monkeypatch.setattr(seed_mod, "get_connection", _fake_get_connection)
    schema_mod.create_tables()
    schema_mod.run_migrations(conn)
    seed_mod.seed_defaults()
    return conn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def builder_conn(monkeypatch):
    """In-memory DB seeded with one AT&T company and one Senior_Designer application."""
    conn = _setup_in_memory_db(monkeypatch)

    cursor = conn.execute(
        "INSERT INTO companies (company_name) VALUES (?)",
        ("AT&T",),
    )
    conn.commit()
    company_id = cursor.lastrowid

    cursor = conn.execute(
        "INSERT INTO applications (company_id, role_title, application_date)"
        " VALUES (?, ?, ?)",
        (company_id, "Senior_Designer", "2024-01-15"),
    )
    conn.commit()
    application_id = cursor.lastrowid

    yield conn, application_id
    conn.close()


@pytest.fixture()
def empty_conn(monkeypatch):
    """In-memory DB with schema, migrations, and seeds but no application rows."""
    conn = _setup_in_memory_db(monkeypatch)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# escape_latex tests (6)
# ---------------------------------------------------------------------------


def test_escape_latex_ampersand():
    """escape_latex escapes & to \\&."""
    assert escape_latex("AT&T") == r"AT\&T"


def test_escape_latex_percent():
    """escape_latex escapes % to \\%."""
    assert escape_latex("50%") == r"50\%"


def test_escape_latex_underscore():
    """escape_latex escapes _ to \\_."""
    assert escape_latex("foo_bar") == r"foo\_bar"


def test_escape_latex_backslash():
    """escape_latex converts a backslash to \\textbackslash{}."""
    assert escape_latex("a\\b") == r"a\textbackslash{}b"


def test_escape_latex_none_returns_dash():
    """escape_latex returns '---' for None input."""
    assert escape_latex(None) == "---"


def test_escape_latex_empty_string():
    """escape_latex returns '' unchanged for empty string input."""
    assert escape_latex("") == ""


# ---------------------------------------------------------------------------
# latex_builder tests (7)
# ---------------------------------------------------------------------------


def test_latex_build_afa_table_returns_non_empty(builder_conn):
    """build_afa_table returns a non-empty string."""
    conn, _ = builder_conn
    result = build_afa_table(conn)
    assert isinstance(result, str) and len(result) > 0


def test_latex_build_afa_table_escapes_company_name(builder_conn):
    """build_afa_table output does not contain the literal string 'AT&T'."""
    conn, _ = builder_conn
    result = build_afa_table(conn)
    assert "AT&T" not in result


def test_latex_build_afa_table_empty_db_no_placeholder(empty_conn):
    """build_afa_table on an empty DB replaces <<TABLE_ROWS>> with empty content."""
    result = build_afa_table(empty_conn)
    assert "<<TABLE_ROWS>>" not in result


def test_latex_build_application_sheet_returns_non_empty(builder_conn):
    """build_application_sheet returns a non-empty string."""
    conn, application_id = builder_conn
    result = build_application_sheet(conn, application_id)
    assert isinstance(result, str) and len(result) > 0


def test_latex_build_analytics_summary_returns_non_empty(builder_conn):
    """build_analytics_summary returns a non-empty string."""
    conn, _ = builder_conn
    result = build_analytics_summary(conn)
    assert isinstance(result, str) and len(result) > 0


def test_write_file_writes_to_disk(tmp_path):
    """write_file creates a file on disk containing the given content."""
    out = str(tmp_path / "test_output.tex")
    write_file("hello latex", out)
    assert Path(out).exists()
    assert Path(out).read_text(encoding="utf-8") == "hello latex"


def test_write_file_raises_on_bad_path():
    """write_file raises IOError or OSError when the destination path is invalid."""
    with pytest.raises((IOError, OSError)):
        write_file("content", "/nonexistent_dir/out.tex")


# ---------------------------------------------------------------------------
# pdf_builder tests (3)
# ---------------------------------------------------------------------------


def test_pdf_build_afa_table(builder_conn, tmp_path):
    """pdf_builder.build_afa_table creates a non-empty PDF file."""
    conn, _ = builder_conn
    out = str(tmp_path / "afa_table.pdf")
    pdf_builder.build_afa_table(conn, out)
    assert os.path.exists(out) and os.path.getsize(out) > 0


def test_pdf_build_application_sheet(builder_conn, tmp_path):
    """pdf_builder.build_application_sheet creates a non-empty PDF file."""
    conn, application_id = builder_conn
    out = str(tmp_path / "application_sheet.pdf")
    pdf_builder.build_application_sheet(conn, out, application_id)
    assert os.path.exists(out) and os.path.getsize(out) > 0


def test_pdf_build_analytics_summary(builder_conn, tmp_path):
    """pdf_builder.build_analytics_summary creates a non-empty PDF file."""
    conn, _ = builder_conn
    out = str(tmp_path / "analytics_summary.pdf")
    pdf_builder.build_analytics_summary(conn, out)
    assert os.path.exists(out) and os.path.getsize(out) > 0


# ---------------------------------------------------------------------------
# docx_builder tests (2)
# ---------------------------------------------------------------------------


def test_docx_build_afa_table(builder_conn, tmp_path):
    """docx_builder.build_afa_table creates a non-empty .docx file."""
    conn, _ = builder_conn
    out = str(tmp_path / "afa_table.docx")
    docx_builder.build_afa_table(conn, out)
    assert os.path.exists(out) and os.path.getsize(out) > 0


def test_docx_build_application_sheet(builder_conn, tmp_path):
    """docx_builder.build_application_sheet creates a non-empty .docx file."""
    conn, application_id = builder_conn
    out = str(tmp_path / "application_sheet.docx")
    docx_builder.build_application_sheet(conn, out, application_id)
    assert os.path.exists(out) and os.path.getsize(out) > 0


# ---------------------------------------------------------------------------
# odt_builder tests (2)
# ---------------------------------------------------------------------------


def test_odt_build_afa_table(builder_conn, tmp_path):
    """odt_builder.build_afa_table creates a non-empty .odt file."""
    conn, _ = builder_conn
    out = str(tmp_path / "afa_table.odt")
    odt_builder.build_afa_table(conn, out)
    assert os.path.exists(out) and os.path.getsize(out) > 0


def test_odt_build_application_sheet(builder_conn, tmp_path):
    """odt_builder.build_application_sheet creates a non-empty .odt file."""
    conn, application_id = builder_conn
    out = str(tmp_path / "application_sheet.odt")
    odt_builder.build_application_sheet(conn, out, application_id)
    assert os.path.exists(out) and os.path.getsize(out) > 0
