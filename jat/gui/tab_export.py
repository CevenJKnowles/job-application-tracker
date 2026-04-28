"""Export tab for the Job Application Tracker."""

import os
from datetime import date

from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QDate, Qt

from jat.database.connection import get_connection
from jat.export import docx_builder, latex_builder, odt_builder, pdf_builder
from jat.gui.dialogs.export_dialog import ExportDialog
from jat.models import application as app_model
from jat.models import reference as ref_model

_REPORT_KEYS = ["afa_table", "application_sheet", "analytics_summary"]
_REPORT_LABELS = ["Application Activity Table", "Application Sheet", "Analytics Summary"]


class ExportTab(QWidget):
    """Tab for configuring and triggering document exports."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Set up the export tab layout."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._build_report_group())
        layout.addWidget(self._build_filter_stack())
        layout.addSpacing(8)
        layout.addWidget(self._build_export_button())
        layout.addWidget(self._build_status_label())
        layout.addStretch()

        self._report_combo.currentIndexChanged.connect(
            self._filter_stack.setCurrentIndex
        )
        self._load_application_combo()

    # ------------------------------------------------------------------
    # Builder helpers
    # ------------------------------------------------------------------

    def _build_report_group(self) -> QGroupBox:
        """Build the Type group box with the report type combo."""
        group = QGroupBox("Type")
        vbox = QVBoxLayout(group)
        self._report_combo = QComboBox()
        self._report_combo.addItems(_REPORT_LABELS)
        vbox.addWidget(self._report_combo)
        return group

    def _build_filter_stack(self) -> QGroupBox:
        """Build the Filter group box containing a stacked widget (one page per report type)."""
        group = QGroupBox("Filter")
        vbox = QVBoxLayout(group)
        self._filter_stack = QStackedWidget()
        self._filter_stack.addWidget(self._build_afa_filter())
        self._filter_stack.addWidget(self._build_app_filter())
        self._filter_stack.addWidget(self._build_analytics_filter())
        vbox.addWidget(self._filter_stack)
        return group

    def _build_afa_filter(self) -> QWidget:
        """Build filter widgets for the Application Activity Table report."""
        widget = QWidget()
        form = QVBoxLayout(widget)
        today = QDate.currentDate()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("From:"))
        self._afa_date_from = QDateEdit(today.addDays(-90))
        self._afa_date_from.setCalendarPopup(True)
        self._afa_date_from.setDisplayFormat("dd.MM.yyyy")
        row1.addWidget(self._afa_date_from)
        row1.addWidget(QLabel("To:"))
        self._afa_date_to = QDateEdit(today)
        self._afa_date_to.setCalendarPopup(True)
        self._afa_date_to.setDisplayFormat("dd.MM.yyyy")
        row1.addWidget(self._afa_date_to)
        row1.addStretch()
        form.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Status:"))
        self._afa_status_combo = QComboBox()
        self._afa_status_combo.addItem("All", userData=None)
        for status in ref_model.get_active("ref_statuses"):
            self._afa_status_combo.addItem(status["label"], userData=status["id"])
        row2.addWidget(self._afa_status_combo)
        row2.addStretch()
        form.addLayout(row2)

        return widget

    def _build_app_filter(self) -> QWidget:
        """Build filter widgets for the Application Sheet report."""
        widget = QWidget()
        hbox = QHBoxLayout(widget)
        hbox.addWidget(QLabel("Application:"))
        self._app_combo = QComboBox()
        self._app_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        hbox.addWidget(self._app_combo)
        return widget

    def _build_analytics_filter(self) -> QWidget:
        """Build filter widgets for the Analytics Summary report."""
        widget = QWidget()
        hbox = QHBoxLayout(widget)
        today = QDate.currentDate()

        hbox.addWidget(QLabel("From:"))
        self._ana_date_from = QDateEdit(today.addDays(-90))
        self._ana_date_from.setCalendarPopup(True)
        self._ana_date_from.setDisplayFormat("dd.MM.yyyy")
        hbox.addWidget(self._ana_date_from)

        hbox.addWidget(QLabel("To:"))
        self._ana_date_to = QDateEdit(today)
        self._ana_date_to.setCalendarPopup(True)
        self._ana_date_to.setDisplayFormat("dd.MM.yyyy")
        hbox.addWidget(self._ana_date_to)
        hbox.addStretch()

        return widget

    def _build_export_button(self) -> QPushButton:
        """Build the full-width Export button."""
        self._export_btn = QPushButton("Export…")
        self._export_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._export_btn.clicked.connect(self._on_export)
        return self._export_btn

    def _build_status_label(self) -> QLabel:
        """Build the status feedback label."""
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        return self._status_label

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_application_combo(self) -> None:
        """Populate the application combo with all applications."""
        self._app_combo.clear()
        for app in app_model.get_all_applications():
            label = (
                f"{app['application_date']} | "
                f"{app['company_name']} | "
                f"{app['role_title']}"
            )
            self._app_combo.addItem(label, userData=app["application_id"])

    # ------------------------------------------------------------------
    # Export handler
    # ------------------------------------------------------------------

    def _on_export(self) -> None:
        """Open ExportDialog and, on confirm, run the selected builders."""
        report_idx = self._report_combo.currentIndex()
        report_type = _REPORT_KEYS[report_idx]
        today_str = date.today().strftime("%Y%m%d")
        base_stem = f"{report_type}_{today_str}"

        dialog = ExportDialog(report_type, base_stem, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        directory = dialog.export_directory
        formats = dialog.selected_formats

        try:
            with get_connection() as conn:
                for fmt in formats:
                    output_path = os.path.join(directory, f"{base_stem}.{fmt}")
                    self._run_builder(conn, report_type, fmt, output_path)

            self._status_label.setStyleSheet("")
            self._status_label.setText(f"Exported to: {directory}")

        except (IOError, OSError, PermissionError) as exc:
            self._status_label.setStyleSheet("color: red;")
            self._status_label.setText(str(exc))
        except Exception as exc:
            self._status_label.setStyleSheet("color: red;")
            self._status_label.setText(str(exc))

    def _run_builder(
        self,
        conn,
        report_type: str,
        fmt: str,
        output_path: str,
    ) -> None:
        """Dispatch a single builder call based on report_type and fmt."""
        if report_type == "afa_table":
            date_from = self._afa_date_from.date().toString("yyyy-MM-dd")
            date_to = self._afa_date_to.date().toString("yyyy-MM-dd")
            status_id = self._afa_status_combo.currentData()
            if fmt == "tex":
                content = latex_builder.build_afa_table(
                    conn, date_from, date_to, status_id
                )
                latex_builder.write_file(content, output_path)
            elif fmt == "pdf":
                pdf_builder.build_afa_table(conn, output_path, date_from, date_to, status_id)
            elif fmt == "docx":
                docx_builder.build_afa_table(conn, output_path, date_from, date_to, status_id)
            elif fmt == "odt":
                odt_builder.build_afa_table(conn, output_path, date_from, date_to, status_id)

        elif report_type == "application_sheet":
            app_id = self._app_combo.currentData()
            if app_id is None:
                raise ValueError("No application selected.")
            if fmt == "tex":
                content = latex_builder.build_application_sheet(conn, app_id)
                latex_builder.write_file(content, output_path)
            elif fmt == "pdf":
                pdf_builder.build_application_sheet(conn, output_path, app_id)
            elif fmt == "docx":
                docx_builder.build_application_sheet(conn, output_path, app_id)
            elif fmt == "odt":
                odt_builder.build_application_sheet(conn, output_path, app_id)

        elif report_type == "analytics_summary":
            date_from = self._ana_date_from.date().toString("yyyy-MM-dd")
            date_to = self._ana_date_to.date().toString("yyyy-MM-dd")
            if fmt == "tex":
                content = latex_builder.build_analytics_summary(conn, date_from, date_to)
                latex_builder.write_file(content, output_path)
            elif fmt == "pdf":
                pdf_builder.build_analytics_summary(conn, output_path, date_from, date_to)
            elif fmt == "docx":
                docx_builder.build_analytics_summary(conn, output_path, date_from, date_to)
            elif fmt == "odt":
                odt_builder.build_analytics_summary(conn, output_path, date_from, date_to)
