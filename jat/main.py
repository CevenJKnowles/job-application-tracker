"""Entry point for the Job Application Tracker application."""

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow

from jat.database.schema import create_tables
from jat.database.seed import seed_defaults


def main() -> None:
    """Initialise the database, then launch the GUI."""
    create_tables()
    seed_defaults()

    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Job Application Tracker")
    window.setMinimumSize(1200, 750)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
