"""Main application window for the Job Application Tracker."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QTextOption
from PyQt6.QtWidgets import QMainWindow, QTabWidget

from jat.gui.style import PLACEHOLDER_COLOUR
from jat.gui.tab_analytics import AnalyticsTab
from jat.gui.tab_applications import ApplicationsTab
from jat.gui.tab_companies import CompaniesTab
from jat.gui.tab_export import ExportTab
from jat.gui.tab_settings import SettingsTab

_GLOBAL_STYLESHEET = f"""
QLineEdit, QPlainTextEdit, QTextEdit {{
    color: placeholder {PLACEHOLDER_COLOUR};
}}
QLineEdit {{
    placeholder-text-color: {PLACEHOLDER_COLOUR};
}}
QPlainTextEdit, QTextEdit {{
    placeholder-text-color: {PLACEHOLDER_COLOUR};
}}
"""


class MainWindow(QMainWindow):
    """Top-level window containing the five-tab navigation."""

    reference_data_changed = pyqtSignal(str)

    def __init__(self) -> None:
        """Set up the window and tab layout."""
        super().__init__()
        self.setWindowTitle("Job Application Tracker")
        self.setMinimumSize(1200, 750)

        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        self._applications_tab = ApplicationsTab()
        self._companies_tab = CompaniesTab()
        self._analytics_tab = AnalyticsTab()
        self._export_tab = ExportTab()
        self._settings_tab = SettingsTab()

        self._tabs.addTab(self._applications_tab, "Applications")
        self._tabs.addTab(self._companies_tab, "Companies")
        self._tabs.addTab(self._analytics_tab, "Analytics")
        self._tabs.addTab(self._export_tab, "Export")
        self._tabs.addTab(self._settings_tab, "Settings")

        self._tabs.currentChanged.connect(self._on_tab_changed)

        # Wire reference-data change signal through main window to consumers
        self._settings_tab.reference_data_changed.connect(self.reference_data_changed)
        self.reference_data_changed.connect(
            self._applications_tab.reload_reference_data
        )

    def _on_tab_changed(self, index: int) -> None:
        """Refresh data-bearing tabs when they come into focus."""
        if index == 0:
            self._applications_tab._load_data()
        elif index == 1:
            self._companies_tab._load_data()
