"""Companies tab: browse, search, and manage company records."""

from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
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

_NUM_COLS = 6

_HEADERS = ["ID", "Company Name", "Industry", "Website", "Applications", "Notes"]

_ROLE_ID = Qt.ItemDataRole.UserRole


class _CompanyFilterProxy(QSortFilterProxyModel):
    """Proxy that filters rows by search text and industry."""

    def __init__(self, parent=None) -> None:
        """Initialise with pass-all filter state."""
        super().__init__(parent)
        self._search = ""
        self._industry = ""

    def set_filters(self, search: str, industry: str) -> None:
        """Update filter criteria and refresh the view."""
        self._search = search.lower()
        self._industry = industry
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        """Return True if the row passes all active filters."""
        model = self.sourceModel()

        if self._search:
            name = (model.item(source_row, _COL_NAME) or QStandardItem()).text()
            ind = (model.item(source_row, _COL_INDUSTRY) or QStandardItem()).text()
            if self._search not in name.lower() and self._search not in ind.lower():
                return False

        if self._industry and self._industry != "All Industries":
            ind = (model.item(source_row, _COL_INDUSTRY) or QStandardItem()).text()
            if ind != self._industry:
                return False

        return True


class CompaniesTab(QWidget):
    """Toolbar + table for company CRUD; client-side search and filter."""

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

        # ── Model + proxy ────────────────────────────────────────────────────
        self._source_model = QStandardItemModel(0, _NUM_COLS)
        self._source_model.setHorizontalHeaderLabels(_HEADERS)

        self._proxy = _CompanyFilterProxy()
        self._proxy.setSourceModel(self._source_model)

        # ── Table view ───────────────────────────────────────────────────────
        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setColumnHidden(_COL_ID, True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionsMovable(True)
        header.setDragEnabled(True)
        header.setSortIndicatorShown(True)
        self._table.setSortingEnabled(True)

        self._table.doubleClicked.connect(self._on_row_double_clicked)
        root.addWidget(self._table)

        self._empty_label = QLabel(
            "No companies yet. Click + Add to begin.", self._table
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()

        # ── Status bar ───────────────────────────────────────────────────────
        self._status_label = QLabel()
        root.addWidget(self._status_label)

        self._load_data()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _selected_company_id(self) -> int | None:
        """Return the database id of the selected row, or None."""
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        source_row = self._proxy.mapToSource(rows[0]).row()
        item = self._source_model.item(source_row, _COL_ID)
        return int(item.text()) if item else None

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

        # Repopulate source model
        self._source_model.setRowCount(0)
        for row in rows:
            id_item = QStandardItem(str(row["id"]))
            name_item = QStandardItem(row["company_name"] or "")
            industry_item = QStandardItem(row["industry"] or "")
            website_item = QStandardItem(row["website"] or "")
            apps_item = QStandardItem(str(row["application_count"]))
            notes_item = QStandardItem(row["notes"] or "")
            self._source_model.appendRow([
                id_item,
                name_item,
                industry_item,
                website_item,
                apps_item,
                notes_item,
            ])

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._update_status(rows)
        self._apply_filter()
        self._refresh_empty_state()

    def _apply_filter(self) -> None:
        """Push current filter criteria to the proxy model."""
        self._proxy.set_filters(
            search=self._search_input.text().strip(),
            industry=self._industry_combo.currentText(),
        )
        self._refresh_empty_state()

    def _refresh_empty_state(self) -> None:
        """Show the empty-state label when no rows are visible; hide it otherwise."""
        visible = self._proxy.rowCount()
        self._empty_label.setGeometry(self._table.rect())
        self._empty_label.setVisible(visible == 0)
        if visible == 0:
            self._empty_label.raise_()

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
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    def _on_edit(self) -> None:
        """Open the Edit Company dialog for the selected row; reload on success."""
        company_id = self._selected_company_id()
        if company_id is None:
            QMessageBox.warning(self, "No Selection", "Select a company to edit.")
            return
        dlg = CompanyForm(parent=self, company_id=company_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    def _on_row_double_clicked(self, index) -> None:
        """Open the Edit Company dialog when a row is double-clicked."""
        company_id = self._selected_company_id()
        if company_id is None:
            return
        dlg = CompanyForm(parent=self, company_id=company_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    def _on_delete(self) -> None:
        """Confirm then delete the selected company; reload on success."""
        company_id = self._selected_company_id()
        if company_id is None:
            QMessageBox.warning(self, "No Selection", "Select a company to delete.")
            return

        sel_rows = self._table.selectionModel().selectedRows()
        if not sel_rows:
            return
        source_row = self._proxy.mapToSource(sel_rows[0]).row()
        name = (self._source_model.item(source_row, _COL_NAME) or QStandardItem()).text()

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
