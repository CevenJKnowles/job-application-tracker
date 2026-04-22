# Installation

## Prerequisites

- Python 3.11 or higher
- Git
- TexMaker (optional — only required to compile `.tex` exports to PDF)

## Setup

```zsh
git clone <repo_url>
cd job-application-tracker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## First Run

```zsh
python -m jat.main
```

The database is created automatically at `data/jat.db` on first run. No manual
setup is required.

## Running Tests

```zsh
pytest
```
