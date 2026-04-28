# Job Application Tracker

A local desktop application for recording, managing, and reporting on job applications throughout the full application lifecycle.

## What it does

Job Application Tracker (JAT) gives you a structured place to record every job application you send, track its progress through phases such as Applied, Interview, and Final Stage, and capture what happened at each step. Each entry stores the company, role title, salary range, work mode, source, and your own notes, alongside a priority score so you can see at a glance which roles matter most to you. The companion Companies tab holds full company records, including contact details and links to relevant job boards. A built-in analytics tab shows charts and summary figures across your job search, and an export tab produces formatted reports as LaTeX, PDF, Word, or ODT files. All data is stored in a local SQLite database on your own machine — nothing is sent anywhere.

<!-- screenshot -->

## Quick start

1. Install [Python 3.11 or higher](https://www.python.org/downloads/) and [Git](https://git-scm.com/).

2. Clone the repository and install dependencies.

   ```zsh
   git clone <repo_url>
   cd job-application-tracker
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Run the app.

   ```zsh
   python -m jat.main
   ```

See [docs/installation.md](docs/installation.md) for the full installation guide, including troubleshooting.

## Features

- Track job applications with status, phase, priority, and salary details
- Manage company records including contacts, industry, and platform links
- Filter applications by status, phase, and category
- Analytics charts via Matplotlib
- Export reports to LaTeX/PDF via TexMaker, and to Word or ODT
- Fully local — no accounts, no cloud, no telemetry

## Tech stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.11+ |
| GUI | PyQt6 |
| Database | SQLite (local file) |
| Charts | Matplotlib |
| Export | LaTeX / TexMaker, fpdf2, python-docx, odfpy |

## Licence

MIT

## Documentation

- [Installation guide](docs/installation.md)
- [User guide](docs/user_guide.md)
