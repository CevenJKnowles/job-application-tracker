"""Dialog for adding or editing a company record."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

import jat.models.company as company_model


class CompanyForm(QDialog):
    """Add or edit a single company. Pass company_id to enter edit mode."""

    def __init__(self, parent=None, company_id: int | None = None) -> None:
        """Build the form; pre-populate fields when company_id is provided."""
        super().__init__(parent)
        self._company_id = company_id
        self._name_conflict = False

        self.setWindowTitle("Edit Company" if company_id is not None else "Add Company")
        self.setMinimumWidth(480)

        root = QVBoxLayout(self)

        # ── Form grid ────────────────────────────────────────────────────────
        form = QGridLayout()
        form.setColumnStretch(1, 1)

        form.addWidget(QLabel("Company Name *"), 0, 0, Qt.AlignmentFlag.AlignTop)
        self._name_edit = QLineEdit()
        form.addWidget(self._name_edit, 0, 1)

        self._name_warning = QLabel("Company name already exists.")
        self._name_warning.setStyleSheet("color: red;")
        self._name_warning.hide()
        form.addWidget(self._name_warning, 1, 1)

        form.addWidget(QLabel("Industry"), 2, 0)
        self._industry_edit = QLineEdit()
        form.addWidget(self._industry_edit, 2, 1)

        form.addWidget(QLabel("Website"), 3, 0)
        self._website_edit = QLineEdit()
        form.addWidget(self._website_edit, 3, 1)

        form.addWidget(QLabel("Notes"), 4, 0, Qt.AlignmentFlag.AlignTop)
        self._notes_edit = QTextEdit()
        self._notes_edit.setFixedHeight(90)
        form.addWidget(self._notes_edit, 4, 1)

        root.addLayout(form)

        # ── Buttons ──────────────────────────────────────────────────────────
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

        # Load names to validate against before connecting signals
        self._existing_names = self._load_existing_names()

        # Pre-populate before wiring so setText doesn't race with an empty set
        if company_id is not None:
            self._populate(company_id)

        self._name_edit.textChanged.connect(self._on_name_changed)
        self._update_ok_button()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _load_existing_names(self) -> set[str]:
        """Return lowercase names of all companies except the one being edited."""
        rows = company_model.get_all_companies()
        return {
            row["company_name"].lower()
            for row in rows
            if row["id"] != self._company_id
        }

    def _populate(self, company_id: int) -> None:
        """Fill fields from the existing company record."""
        row = company_model.get_company_by_id(company_id)
        if row is None:
            return
        self._name_edit.setText(row["company_name"] or "")
        self._industry_edit.setText(row["industry"] or "")
        self._website_edit.setText(row["website"] or "")
        self._notes_edit.setPlainText(row["notes"] or "")

    def _on_name_changed(self, text: str) -> None:
        """Update the conflict flag and warning label on every keystroke."""
        self._name_conflict = text.strip().lower() in self._existing_names
        self._name_warning.setVisible(self._name_conflict)
        self._update_ok_button()

    def _update_ok_button(self) -> None:
        """Disable OK when the name field is empty or conflicts with another company."""
        name_filled = bool(self._name_edit.text().strip())
        self._ok_btn.setEnabled(name_filled and not self._name_conflict)

    # ── Slot handlers ────────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        """Persist the form data; keep the dialog open on error."""
        name = self._name_edit.text().strip()
        industry = self._industry_edit.text().strip()
        website = self._website_edit.text().strip()
        notes = self._notes_edit.toPlainText().strip()

        try:
            if self._company_id is None:
                company_model.add_company(name, industry, website, notes)
            else:
                company_model.update_company(
                    self._company_id, name, industry, website, notes
                )
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return

        self.accept()
