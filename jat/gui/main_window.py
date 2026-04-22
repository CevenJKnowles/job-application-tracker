"""Main application window for the Job Application Tracker."""

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget

from jat.gui.tab_applications import ApplicationsTab
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

        self._applications_tab = ApplicationsTab()
        self._companies_tab = CompaniesTab()
        self._tabs.addTab(self._applications_tab, "Applications")
        self._tabs.addTab(self._companies_tab, "Companies")
        self._tabs.addTab(QWidget(), "Analytics")
        self._tabs.addTab(QWidget(), "Export")
        self._tabs.addTab(SettingsTab(), "Settings")

        self._tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        """Refresh data-bearing tabs when they come into focus."""
        if index == 0:
            self._applications_tab._load_data()
        elif index == 1:
            self._companies_tab._load_data()
