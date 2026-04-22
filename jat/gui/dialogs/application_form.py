"""Dialog for adding or editing a job application."""

from __future__ import annotations

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

import jat.models.application as app_model
import jat.models.company as company_model
import jat.models.reference as ref_model
from jat.gui.dialogs.company_form import CompanyForm

_ADD_NEW_SENTINEL = "Add new company..."

_REF_TABLES: tuple[tuple[str, str, str], ...] = (
    ("status_id", "ref_statuses", "Status"),
    ("category_id", "ref_categories", "Category"),
    ("employment_type_id", "ref_employment_types", "Employment Type"),
    ("source_id", "ref_sources", "Source"),
    ("work_mode_id", "ref_work_modes", "Work Mode"),
    ("currency_id", "ref_currencies", "Currency"),
)


class ApplicationForm(QDialog):
    """Add or edit a single application. Pass application_id for edit mode."""

    def __init__(self, parent=None, application_id: int | None = None) -> None:
        """Build the form; pre-populate fields when application_id is provided."""
        super().__init__(parent)
        self._application_id = application_id
        self._prev_company_index = 0

        title = (
            "Edit Application" if application_id is not None else "Add Application"
        )
        self.setWindowTitle(title)
        self.setMinimumWidth(560)

        root = QVBoxLayout(self)

        # ── Form grid ────────────────────────────────────────────────────────
        form = QGridLayout()
        form.setColumnStretch(1, 1)
        row = 0

        form.addWidget(QLabel("Role Title *"), row, 0, Qt.AlignmentFlag.AlignTop)
        self._role_title = QLineEdit()
        form.addWidget(self._role_title, row, 1)
        row += 1

        form.addWidget(QLabel("Company *"), row, 0)
        self._company_combo = QComboBox()
        self._load_companies()
        form.addWidget(self._company_combo, row, 1)
        row += 1

        form.addWidget(QLabel("Application Date *"), row, 0)
        self._application_date = QDateEdit()
        self._application_date.setCalendarPopup(True)
        self._application_date.setDate(QDate.currentDate())
        form.addWidget(self._application_date, row, 1)
        row += 1

        form.addWidget(QLabel("Response Date"), row, 0)
        self._response_date_check = QCheckBox("Set response date")
        self._response_date = QDateEdit()
        self._response_date.setCalendarPopup(True)
        self._response_date.setDate(QDate.currentDate())
        self._response_date.setEnabled(False)
        response_row_layout = QHBoxLayout()
        response_row_layout.setContentsMargins(0, 0, 0, 0)
        response_row_layout.addWidget(self._response_date_check)
        response_row_layout.addWidget(self._response_date)
        form.addLayout(response_row_layout, row, 1)
        row += 1

        self._ref_combos: dict[str, QComboBox] = {}
        for field, table, label in _REF_TABLES:
            form.addWidget(QLabel(label), row, 0)
            combo = QComboBox()
            self._populate_ref_combo(combo, table)
            self._ref_combos[field] = combo
            form.addWidget(combo, row, 1)
            row += 1

        form.addWidget(QLabel("Priority Score"), row, 0)
        self._priority_score = QSpinBox()
        self._priority_score.setMinimum(1)
        self._priority_score.setMaximum(5)
        self._priority_score.setValue(3)
        form.addWidget(self._priority_score, row, 1)
        row += 1

        form.addWidget(QLabel("Follow-up Date"), row, 0)
        self._follow_up_check = QCheckBox("Set follow-up date")
        self._follow_up_date = QDateEdit()
        self._follow_up_date.setCalendarPopup(True)
        self._follow_up_date.setDate(QDate.currentDate())
        self._follow_up_date.setEnabled(False)
        follow_row_layout = QHBoxLayout()
        follow_row_layout.setContentsMargins(0, 0, 0, 0)
        follow_row_layout.addWidget(self._follow_up_check)
        follow_row_layout.addWidget(self._follow_up_date)
        form.addLayout(follow_row_layout, row, 1)
        row += 1

        form.addWidget(QLabel("Job Posting URL"), row, 0)
        self._job_posting_url = QLineEdit()
        form.addWidget(self._job_posting_url, row, 1)
        row += 1

        form.addWidget(QLabel("City"), row, 0)
        self._city = QLineEdit()
        form.addWidget(self._city, row, 1)
        row += 1

        form.addWidget(QLabel("Country"), row, 0)
        self._country = QLineEdit()
        form.addWidget(self._country, row, 1)
        row += 1

        form.addWidget(QLabel("Salary Min"), row, 0)
        self._salary_min = QDoubleSpinBox()
        self._salary_min.setMinimum(0.0)
        self._salary_min.setMaximum(9_999_999.0)
        self._salary_min.setDecimals(2)
        self._salary_min.setValue(0.0)
        form.addWidget(self._salary_min, row, 1)
        row += 1

        form.addWidget(QLabel("Salary Max"), row, 0)
        self._salary_max = QDoubleSpinBox()
        self._salary_max.setMinimum(0.0)
        self._salary_max.setMaximum(9_999_999.0)
        self._salary_max.setDecimals(2)
        self._salary_max.setValue(0.0)
        form.addWidget(self._salary_max, row, 1)
        row += 1

        form.addWidget(QLabel("Notes"), row, 0, Qt.AlignmentFlag.AlignTop)
        self._notes = QTextEdit()
        self._notes.setFixedHeight(90)
        form.addWidget(self._notes, row, 1)

        root.addLayout(form)

        # ── Buttons ──────────────────────────────────────────────────────────
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setEnabled(False)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

        # ── Wire signals ─────────────────────────────────────────────────────
        self._role_title.textChanged.connect(self._update_ok_button)
        self._company_combo.activated.connect(self._on_company_changed)
        self._response_date_check.toggled.connect(self._response_date.setEnabled)
        self._follow_up_check.toggled.connect(self._follow_up_date.setEnabled)

        if application_id is not None:
            self._populate(application_id)

        self._update_ok_button()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _load_companies(self) -> None:
        """Reload the company combo from the database."""
        self._company_combo.blockSignals(True)
        self._company_combo.clear()
        self._company_combo.addItem(_ADD_NEW_SENTINEL, None)
        for c in company_model.get_all_companies():
            self._company_combo.addItem(c["company_name"], c["id"])
        self._company_combo.blockSignals(False)

    def _populate_ref_combo(self, combo: QComboBox, table: str) -> None:
        """Add a blank first item then all active rows from table into combo."""
        combo.clear()
        combo.addItem("", None)
        for item in ref_model.get_active(table):
            combo.addItem(item["label"], item["id"])

    def _set_combo_by_data(self, combo: QComboBox, value) -> None:
        """Select the combo item whose stored data equals value."""
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _populate(self, application_id: int) -> None:
        """Fill all widgets from the existing application record."""
        record = app_model.get_application_by_id(application_id)
        if record is None:
            return

        self._role_title.setText(record["role_title"] or "")
        self._set_combo_by_data(self._company_combo, record["company_id"])

        if record["application_date"]:
            self._application_date.setDate(
                QDate.fromString(record["application_date"], "yyyy-MM-dd")
            )

        if record["response_date"]:
            self._response_date_check.setChecked(True)
            self._response_date.setEnabled(True)
            self._response_date.setDate(
                QDate.fromString(record["response_date"], "yyyy-MM-dd")
            )

        for field, _table, _label in _REF_TABLES:
            self._set_combo_by_data(self._ref_combos[field], record[field])

        if record["priority_score"] is not None:
            self._priority_score.setValue(int(record["priority_score"]))

        if record["follow_up_date"]:
            self._follow_up_check.setChecked(True)
            self._follow_up_date.setEnabled(True)
            self._follow_up_date.setDate(
                QDate.fromString(record["follow_up_date"], "yyyy-MM-dd")
            )

        self._job_posting_url.setText(record["job_posting_url"] or "")
        self._city.setText(record["city"] or "")
        self._country.setText(record["country"] or "")

        if record["salary_min"] is not None:
            self._salary_min.setValue(float(record["salary_min"]))
        if record["salary_max"] is not None:
            self._salary_max.setValue(float(record["salary_max"]))

        self._notes.setPlainText(record["notes"] or "")

    def _update_ok_button(self) -> None:
        """Enable OK only when role_title has content."""
        self._ok_btn.setEnabled(bool(self._role_title.text().strip()))

    def _on_company_changed(self, index: int) -> None:
        """Track valid selections; open CompanyForm when the sentinel is chosen."""
        if self._company_combo.itemData(index) is not None:
            self._prev_company_index = index
            return

        # Sentinel selected — open the add-company dialog
        dlg = CompanyForm(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            old_ids = {
                self._company_combo.itemData(i)
                for i in range(1, self._company_combo.count())
            }
            self._load_companies()
            new_id = next(
                (
                    self._company_combo.itemData(i)
                    for i in range(1, self._company_combo.count())
                    if self._company_combo.itemData(i) not in old_ids
                ),
                None,
            )
            if new_id is not None:
                self._set_combo_by_data(self._company_combo, new_id)
            else:
                self._company_combo.blockSignals(True)
                self._company_combo.setCurrentIndex(self._prev_company_index)
                self._company_combo.blockSignals(False)
        else:
            self._company_combo.blockSignals(True)
            self._company_combo.setCurrentIndex(self._prev_company_index)
            self._company_combo.blockSignals(False)

    # ── Slot handlers ────────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        """Collect form data, validate, and call the appropriate model function."""
        role_title = self._role_title.text().strip()
        company_id = self._company_combo.currentData()
        application_date = self._application_date.date().toString("yyyy-MM-dd")

        if company_id is None:
            QMessageBox.warning(self, "Validation Error", "Please select a company.")
            return

        url = self._job_posting_url.text().strip()
        if url and not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "Job posting URL must start with http:// or https://.",
            )
            return

        kwargs: dict = {
            "response_date": (
                self._response_date.date().toString("yyyy-MM-dd")
                if self._response_date_check.isChecked()
                else None
            ),
            "follow_up_date": (
                self._follow_up_date.date().toString("yyyy-MM-dd")
                if self._follow_up_check.isChecked()
                else None
            ),
            "job_posting_url": url or None,
            "city": self._city.text().strip() or None,
            "country": self._country.text().strip() or None,
            "salary_min": (
                self._salary_min.value() if self._salary_min.value() > 0 else None
            ),
            "salary_max": (
                self._salary_max.value() if self._salary_max.value() > 0 else None
            ),
            "priority_score": self._priority_score.value(),
            "notes": self._notes.toPlainText().strip() or None,
        }
        for field in self._ref_combos:
            kwargs[field] = self._ref_combos[field].currentData()

        try:
            if self._application_id is None:
                app_model.add_application(
                    company_id=company_id,
                    role_title=role_title,
                    application_date=application_date,
                    **kwargs,
                )
            else:
                app_model.update_application(
                    self._application_id,
                    company_id=company_id,
                    role_title=role_title,
                    application_date=application_date,
                    **kwargs,
                )
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return

        self.accept()
