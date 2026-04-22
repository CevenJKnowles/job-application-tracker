# CLAUDE.md | Job Application Tracker

This file is read automatically by Claude Code at the start of every session.
Do not delete or move it. Keep it up to date as the project evolves.

---

## Project Identity

**Name:** Job Application Tracker (JAT)
**Package:** `jat`
**Version:** Phase 1 in progress
**Python:** 3.11+
**Licence:** MIT
**Owner:** CevenJKnowles
**Repos:**
- Application code: `job-application-tracker`
- Documentation: `job-application-tracker-dev`

---

## Purpose

A local desktop application for recording, managing, and reporting on job
applications. Built with PyQt6, SQLite, Matplotlib, and LaTeX export.
Designed as a compact internal product, not a personal spreadsheet.

---

## Technology Stack

| Layer | Technology |
|---|---|
| GUI | PyQt6 |
| Database | SQLite via `sqlite3` standard library |
| Analytics / Charts | Matplotlib with `FigureCanvasQTAgg` PyQt6 bridge |
| Document export | LaTeX (.tex file generation, compiled externally in TexMaker) |
| Testing | pytest |
| Formatting | Black (line length 88) |
| Linting | Ruff |

---

## Project Structure

```
jat/
├── main.py                  # Entry point — initialises DB, launches GUI
├── database/
│   ├── connection.py        # SQLite connection manager (context manager pattern)
│   ├── schema.py            # Table creation, idempotent on re-run
│   └── seed.py              # Default reference data, inserts only if tables empty
├── models/
│   ├── application.py       # Application CRUD and queries
│   ├── company.py           # Company CRUD and queries
│   └── reference.py         # Generic reference table CRUD
├── gui/
│   ├── main_window.py       # QMainWindow with QTabWidget (5 tabs)
│   ├── tab_applications.py
│   ├── tab_companies.py
│   ├── tab_analytics.py
│   ├── tab_export.py
│   ├── tab_settings.py
│   └── dialogs/
│       ├── application_form.py
│       ├── company_form.py
│       └── confirm_dialog.py
├── analytics/
│   ├── queries.py           # All analytics SQL as named functions
│   └── charts.py            # Matplotlib figure builders
└── export/
    ├── latex_builder.py     # Template reader, data injector, .tex writer
    └── templates/
        ├── afa_table.tex
        ├── application_sheet.tex
        └── analytics_summary.tex
```

---

## Database Schema

### Table: `applications`

```sql
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
);
```

### Table: `companies`

```sql
CREATE TABLE IF NOT EXISTS companies (
    company_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name        TEXT NOT NULL UNIQUE,
    company_website     TEXT,
    industry            TEXT,
    company_size_band   TEXT,
    linkedin_url        TEXT,
    created_at          DATETIME DEFAULT (datetime('now', 'localtime'))
);
```

### Reference Tables (all follow this pattern)

Tables: `ref_statuses`, `ref_categories`, `ref_employment_types`,
`ref_sources`, `ref_work_modes`, `ref_currencies`

```sql
CREATE TABLE IF NOT EXISTS ref_statuses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    label       TEXT NOT NULL,
    sort_order  INTEGER DEFAULT 0,
    is_active   INTEGER DEFAULT 1
);
```

### Default Reference Values

**ref_statuses:** Applied, Reviewing, Interview, Final Stage, Offer, Rejected, Withdrawn, Ghosted

**ref_categories:** Product Design, UX/UI Design, Service Design, Creative Direction,
AI Strategy, Prompt Engineering, Innovation, Research, Marketing, Operations

**ref_employment_types:** Full-time, Part-time, Contract, Freelance, Internship, Temporary

**ref_sources:** LinkedIn, Company Website, Referral, Recruiter Outreach, Indeed,
Glassdoor, Networking, Other

**ref_work_modes:** Onsite, Hybrid, Remote

**ref_currencies:** EUR, GBP, USD, CHF

---

## Coding Standards

### Python

- All names use `snake_case` for variables, functions, and modules
- All class names use `PascalCase`
- Constants use `UPPER_SNAKE_CASE`
- Private methods use a `_leading_underscore`
- Maximum line length: 88 characters (Black default)
- All functions have docstrings (one-line minimum)
- No bare `except:` clauses; always catch specific exceptions

### SQL

- Always use parameterised queries. Never format user input directly into SQL strings.
- Correct: `cursor.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,))`
- Incorrect: `cursor.execute(f"SELECT * FROM companies WHERE company_id = {company_id}")`
- Table names are plural `snake_case`
- Reference tables are prefixed `ref_`
- Primary keys follow the pattern `{singular_table_name}_id`
- Foreign key column names match the referenced primary key exactly

### PyQt6

- Never mix database logic into GUI classes. GUI classes call model functions; they do not run SQL directly.
- All modal dialogs inherit from `QDialog`
- All destructive actions (delete, deactivate, reset) require the `ConfirmDialog` before executing
- Signal/slot connections use the `widget.signal.connect(handler)` syntax
- Layouts: use `QVBoxLayout` and `QHBoxLayout` as default; `QGridLayout` for forms
- Always call `setWindowTitle()` and `setMinimumSize()` on the main window

### LaTeX Export

- Escape these characters in all user-supplied data before injecting into templates:
  `&` `%` `$` `#` `_` `{` `}` `~` `^` `\`
- Use `\texttt{}` for URLs in LaTeX output
- Document class for all templates: `scrartcl` with `a4paper` option

---

## Architectural Rules

These rules must be followed in every code generation task:

1. **Separation of concerns.** Database in `database/`, business logic in `models/`, presentation in `gui/`. No SQL in GUI files.
2. **Parameterised queries always.** See SQL standards above.
3. **Soft delete for reference values.** Set `is_active = 0`, never `DELETE` a reference row.
4. **Idempotent schema.** `schema.py` must be safe to run multiple times without error. Use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`.
5. **Timestamps automatic.** `created_at` and `updated_at` are set by the database default or by the model layer. Never by the GUI.
6. **Company uniqueness.** `company_name` is unique at the database level. The GUI must also check for duplicates before attempting insert and show a user-facing warning.
7. **Priority score range.** Enforced by `CHECK` constraint in schema and by a `QSpinBox(minimum=1, maximum=5)` in the form.
8. **No orphaned companies.** Deleting a company with linked applications is blocked at the model layer, with a clear error message returned to the GUI.

---

## Current Milestone

**Active:** See `job-application-tracker-dev/06_phases/phase1_scope.md` for the
current milestone and its completion criteria.

Update this section at the start of each new milestone:

```
Active milestone: M5 | Analytics Tab
Status: Not started
Last session: 2026-04-22

Completed: M4 | Applications Tab and Forms — 2026-04-22
```

---

## File Locations

| File | Path |
|---|---|
| Database (runtime) | `data/jat.db` |
| LaTeX templates | `jat/export/templates/` |
| Application icons | `assets/icons/` |
| Tests | `tests/` |
| User documentation | `docs/` |

---

## How to Run

```zsh
# First time setup
cd /home/cjk/Dev/job-application-tracker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Every subsequent session
source .venv/bin/activate
python -m jat.main

# Run tests
pytest
```

---

## Out of Scope for Phase 1

Do not implement the following until Phase 1 is complete and tagged `v1.0.0`:

- Recruiter contacts
- Interview rounds tracker
- CV and cover letter version tracking
- Tags system
- Weighted desirability scoring
- Kanban pipeline dashboard
- Automated reminders
- xlsx export

If asked to implement any of the above during a Phase 1 session, decline and
log it in the Phase 2 backlog at
`job-application-tracker-dev/06_phases/phase2_backlog.md`.
