# Installation

## Requirements

- **Python 3.11 or higher** — [python.org](https://www.python.org/downloads/)
- **Git** — [git-scm.com](https://git-scm.com/)
- **TexMaker** (optional) — only needed if you intend to compile `.tex` exports to PDF. The rest of the app works fully without it.

All other dependencies install automatically via `pip` in the steps below.

## Installation (non-technical users)

These steps use the terminal (on Manjaro, open it from the application menu or press Super and search for "Terminal").

**1. Clone the repository.**

This downloads a copy of the application to your computer.

```zsh
git clone <repo_url>
```

**2. Move into the project folder.**

```zsh
cd job-application-tracker
```

**3. Create and activate a virtual environment.**

A virtual environment is a self-contained folder that keeps this app's Python packages separate from the rest of your system, so nothing interferes with other software you have installed.

```zsh
python -m venv .venv
source .venv/bin/activate
```

Your terminal prompt will change to show `(.venv)` when the environment is active. You will need to run the `source` command again each time you open a new terminal session before running the app.

**4. Install the dependencies.**

```zsh
pip install -r requirements.txt
```

**5. Run the application.**

```zsh
python -m jat.main
```

## Installation (developers)

Follow steps 1–4 above, then use these additional commands as needed.

**Run the test suite:**

```zsh
pytest
```

**Format the code with Black:**

```zsh
black jat/
```

**Lint with Ruff:**

```zsh
ruff check jat/
```

## First run

The database is created automatically at `data/jat.db` the first time the app launches. No manual setup or configuration is required — the app creates all tables and seeds the reference data on startup. You can close and reopen the app freely; your data persists in that file.

## Troubleshooting

**The app does not launch.**
Check that you are running Python 3.11 or higher:

```zsh
python --version
```

If the version shown is below 3.11, install a newer release from [python.org](https://www.python.org/downloads/).

**PyQt6 error mentioning the platform or display.**
On Wayland, set the platform hint before running the app:

```zsh
QT_QPA_PLATFORM=wayland python -m jat.main
```

**TexMaker is not found when exporting.**
TexMaker is a separate application and is not installed by `pip`. Install it through your package manager:

```zsh
sudo pacman -S texmaker
```

Alternatively, download it from [texmaker.sourceforge.net](https://www.xm1math.net/texmaker/). The rest of the app — including all other export formats — works without TexMaker installed.
