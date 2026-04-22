"""Entry point for the Job Application Tracker application."""

import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from jat.database.connection import get_connection
from jat.database.schema import create_tables, run_migrations
from jat.database.seed import seed_defaults
from jat.gui.main_window import MainWindow


def main() -> None:
    """Initialise the database, then launch the GUI."""
    create_tables()
    with get_connection() as conn:
        run_migrations(conn)
    seed_defaults()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/icons/jat_icon.png"))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
