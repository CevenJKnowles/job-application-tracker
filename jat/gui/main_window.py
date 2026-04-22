"""Main application window for the Job Application Tracker."""

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget

from jat.gui.tab_companies import CompaniesTab
from jat.gui.tab_settings import SettingsTab


class MainWindow(QMainWindow):
    """Top-level window containing the five-tab navigation."""

    def __init__(self) -> None:
        """Set up the window and tab layout."""
        super().__init__()
        self.setWindowTitle("Job Application Tracker")
        self.setMinimumSize(1200, 750)

        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        self._tabs.addTab(QWidget(), "Applications")
        self._tabs.addTab(CompaniesTab(), "Companies")
        self._tabs.addTab(QWidget(), "Analytics")
        self._tabs.addTab(QWidget(), "Export")
        self._tabs.addTab(SettingsTab(), "Settings")
