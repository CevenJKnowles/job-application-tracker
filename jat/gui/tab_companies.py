"""Companies tab: browse, search, and manage company records."""

from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import jat.models.company as company_model
from jat.gui.dialogs.company_form import CompanyForm
from jat.gui.dialogs.confirm_dialog import ConfirmDialog

_COL_ID = 0
_COL_NAME = 1
_COL_INDUSTRY = 2
_COL_WEBSITE = 3
_COL_APPLICATIONS = 4
_COL_NOTES = 5


class CompaniesTab(QWidget):
    """Left toolbar + table for company CRUD; client-side search and filter."""

    def __init__(self, parent=None) -> None:
        """Build the toolbar, table, and status bar."""
        super().__init__(parent)

        root = QVBoxLayout(self)

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self._btn_add = QPushButton("Add")
        self._btn_add.clicked.connect(self._on_add)
        toolbar.addWidget(self._btn_add)

        self._btn_edit = QPushButton("Edit")
        self._btn_edit.clicked.connect(self._on_edit)
        toolbar.addWidget(self._btn_edit)

        self._btn_delete = QPushButton("Delete")
        self._btn_delete.clicked.connect(self._on_delete)
        toolbar.addWidget(self._btn_delete)

        toolbar.addStretch()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search name or industry…")
        self._search_input.setFixedWidth(240)
        self._search_input.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._search_input)

        self._industry_combo = QComboBox()
        self._industry_combo.setMinimumWidth(160)
        self._industry_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self._industry_combo)

        root.addLayout(toolbar)

        # ── Table ────────────────────────────────────────────────────────────
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["ID", "Company Name", "Industry", "Website", "Applications", "Notes"]
        )
        self._table.setColumnHidden(_COL_ID, True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table)

        # ── Status bar ───────────────────────────────────────────────────────
        self._status_label = QLabel()
        root.addWidget(self._status_label)

        self._load_data()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _selected_company_id(self) -> int | None:
        """Return the database id of the selected row, or None."""
        indexes = self._table.selectedIndexes()
        if not indexes:
            return None
        return int(self._table.item(indexes[0].row(), _COL_ID).text())

    def _load_data(self) -> None:
        """Fetch all companies from the model, repopulate the table and filter combo."""
        rows = company_model.get_all_companies()

        # Refresh industry combo, preserving the current selection
        current_industry = self._industry_combo.currentText()
        industries = sorted({row["industry"] for row in rows if row["industry"]})
        self._industry_combo.blockSignals(True)
        self._industry_combo.clear()
        self._industry_combo.addItem("All Industries")
        for ind in industries:
            self._industry_combo.addItem(ind)
        idx = self._industry_combo.findText(current_industry)
        self._industry_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._industry_combo.blockSignals(False)

        # Repopulate table
        self._table.setRowCount(0)
        for row in rows:
            visual = self._table.rowCount()
            self._table.insertRow(visual)
            self._table.setItem(visual, _COL_ID, QTableWidgetItem(str(row["id"])))
            self._table.setItem(
                visual, _COL_NAME, QTableWidgetItem(row["company_name"] or "")
            )
            self._table.setItem(
                visual, _COL_INDUSTRY, QTableWidgetItem(row["industry"] or "")
            )
            self._table.setItem(
                visual, _COL_WEBSITE, QTableWidgetItem(row["website"] or "")
            )
            self._table.setItem(
                visual,
                _COL_APPLICATIONS,
                QTableWidgetItem(str(row["application_count"])),
            )
            self._table.setItem(
                visual, _COL_NOTES, QTableWidgetItem(row["notes"] or "")
            )

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._update_status(rows)
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Show/hide rows based on the search input and industry combo. No DB call."""
        search = self._search_input.text().strip().lower()
        industry_filter = self._industry_combo.currentText()
        all_industries = industry_filter == "All Industries"

        for row in range(self._table.rowCount()):
            name_text = (self._table.item(row, _COL_NAME) or QTableWidgetItem("")).text()
            ind_text = (
                self._table.item(row, _COL_INDUSTRY) or QTableWidgetItem("")
            ).text()

            matches_search = (
                not search
                or search in name_text.lower()
                or search in ind_text.lower()
            )
            matches_industry = all_industries or ind_text == industry_filter

            self._table.setRowHidden(row, not (matches_search and matches_industry))

    def _update_status(self, rows) -> None:
        """Update the status label with total company and application counts."""
        total_apps = sum(row["application_count"] for row in rows)
        self._status_label.setText(
            f"{len(rows)} companies | {total_apps} applications total"
        )

    # ── Slot handlers ────────────────────────────────────────────────────────

    def _on_add(self) -> None:
        """Open the Add Company dialog; reload on success."""
        dlg = CompanyForm(parent=self)
        if dlg.exec() == CompanyForm.DialogCode.Accepted:
            self._load_data()

    def _on_edit(self) -> None:
        """Open the Edit Company dialog for the selected row; reload on success."""
        company_id = self._selected_company_id()
        if company_id is None:
            QMessageBox.warning(self, "No Selection", "Select a company to edit.")
            return
        dlg = CompanyForm(parent=self, company_id=company_id)
        if dlg.exec() == CompanyForm.DialogCode.Accepted:
            self._load_data()

    def _on_delete(self) -> None:
        """Confirm then delete the selected company; reload on success."""
        company_id = self._selected_company_id()
        if company_id is None:
            QMessageBox.warning(self, "No Selection", "Select a company to delete.")
            return

        row_index = self._table.selectedIndexes()[0].row()
        name = self._table.item(row_index, _COL_NAME).text()

        dlg = ConfirmDialog(
            f"Delete '{name}'?\n\nThis action cannot be undone.", parent=self
        )
        if dlg.exec() != ConfirmDialog.DialogCode.Accepted:
            return

        try:
            company_model.delete_company(company_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot Delete", str(exc))
            return

        self._load_data()
