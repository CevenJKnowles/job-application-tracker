"""Applications tab: browse, search, and manage application records."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtGui import QColor, QStandardItem, QStandardItemModel
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

import jat.models.application as application_model
import jat.models.reference as ref_model
from jat.gui.dialogs.application_form import ApplicationForm
from jat.gui.dialogs.confirm_dialog import ConfirmDialog

# Column indices — col 0 is hidden ID
_COL_ID = 0
_COL_DATE_APPLIED = 1
_COL_COMPANY = 2
_COL_ROLE = 3
_COL_STATUS = 4
_COL_PHASE = 5
_COL_DATE_MODIFIED = 6
_COL_CATEGORY = 7
_COL_PRIORITY = 8

_NUM_COLS = 9

_HEADERS = [
    "ID",
    "Date Applied",
    "Company",
    "Role",
    "Status",
    "Phase",
    "Date Modified",
    "Category",
    "Priority",
]

_STATUS_BG: dict[str, str] = {
    "Reviewing": "#F9E79F",
    "Rejected": "#F1948A",
    "Ghosted": "#F0B27A",
    "Testing": "#E8DAEF",
}
_STATUS_FG: dict[str, str] = {}

_PHASE_BG: dict[str, str] = {
    "Applied": "#AED6F1",
    "Final Stage": "#76D7C4",
    "Withdrawn": "#D5D8DC",
    "Offer": "#27AE60",
}
_PHASE_FG: dict[str, str] = {
    "Offer": "#FFFFFF",
}

# UserRole stores IDs for filter matching; UserRole+1 stores sort value for dates
_ROLE_ID = Qt.ItemDataRole.UserRole


class _AppFilterProxy(QSortFilterProxyModel):
    """Proxy that filters rows by search text, status, phase, and category."""

    def __init__(self, parent=None) -> None:
        """Initialise with empty (pass-all) filter state."""
        super().__init__(parent)
        self._search = ""
        self._status_id: int | None = None
        self._phase_id: int | None = None
        self._category_id: int | None = None

    def set_filters(
        self,
        search: str,
        status_id: int | None,
        phase_id: int | None,
        category_id: int | None,
    ) -> None:
        """Update all filter criteria and invalidate so the view refreshes."""
        self._search = search.lower()
        self._status_id = status_id
        self._phase_id = phase_id
        self._category_id = category_id
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        """Return True if the row passes all active filters."""
        model = self.sourceModel()

        if self._search:
            company = (model.item(source_row, _COL_COMPANY) or QStandardItem()).text()
            role = (model.item(source_row, _COL_ROLE) or QStandardItem()).text()
            if self._search not in company.lower() and self._search not in role.lower():
                return False

        if self._status_id is not None:
            item = model.item(source_row, _COL_STATUS)
            if item is None or item.data(_ROLE_ID) != self._status_id:
                return False

        if self._phase_id is not None:
            item = model.item(source_row, _COL_PHASE)
            if item is None or item.data(_ROLE_ID) != self._phase_id:
                return False

        if self._category_id is not None:
            item = model.item(source_row, _COL_CATEGORY)
            if item is None or item.data(_ROLE_ID) != self._category_id:
                return False

        return True


class ApplicationsTab(QWidget):
    """Toolbar + table for application CRUD; client-side search and filter."""

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
        self._btn_edit.clicked.connect(self._edit_application)
        toolbar.addWidget(self._btn_edit)

        self._btn_delete = QPushButton("Delete")
        self._btn_delete.clicked.connect(self._on_delete)
        toolbar.addWidget(self._btn_delete)

        toolbar.addStretch()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search role or notes...")
        self._search_input.setFixedWidth(240)
        self._search_input.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self._search_input)

        self._status_combo = QComboBox()
        self._status_combo.setMinimumWidth(140)
        self._status_combo.addItem("All Statuses", None)
        for item in ref_model.get_all_statuses():
            self._status_combo.addItem(item["label"], item["id"])
        self._status_combo.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self._status_combo)

        self._phase_combo = QComboBox()
        self._phase_combo.setMinimumWidth(140)
        self._phase_combo.addItem("All Phases", None)
        for item in ref_model.get_all_phases():
            self._phase_combo.addItem(item["label"], item["id"])
        self._phase_combo.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self._phase_combo)

        self._category_combo = QComboBox()
        self._category_combo.setMinimumWidth(160)
        self._category_combo.addItem("All Categories", None)
        for item in ref_model.get_active("ref_categories"):
            self._category_combo.addItem(item["label"], item["id"])
        self._category_combo.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self._category_combo)

        root.addLayout(toolbar)

        # ── Model + proxy ────────────────────────────────────────────────────
        self._source_model = QStandardItemModel(0, _NUM_COLS)
        self._source_model.setHorizontalHeaderLabels(_HEADERS)

        self._proxy = _AppFilterProxy()
        self._proxy.setSourceModel(self._source_model)

        # ── Table view ───────────────────────────────────────────────────────
        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setColumnHidden(_COL_ID, True)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setWordWrap(True)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionsMovable(True)
        header.setDragEnabled(True)
        header.setSortIndicatorShown(True)
        self._table.setSortingEnabled(True)

        self._table.doubleClicked.connect(lambda _: self._edit_application())
        root.addWidget(self._table)

        self._empty_label = QLabel(
            "No applications yet. Click Add to begin.", self._table
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()

        # ── Status bar ───────────────────────────────────────────────────────
        self._status_label = QLabel()
        root.addWidget(self._status_label)

        self._load_data()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _selected_application_id(self) -> int | None:
        """Return the application_id of the selected row, or None."""
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        source_row = self._proxy.mapToSource(rows[0]).row()
        item = self._source_model.item(source_row, _COL_ID)
        return int(item.text()) if item else None

    def _load_data(self) -> None:
        """Fetch all applications from the model and repopulate the table."""
        rows = application_model.get_all_applications()
        self._source_model.setRowCount(0)

        for row_data in rows:
            # Build a full row of QStandardItems
            id_item = QStandardItem(str(row_data["application_id"]))

            date_item = QStandardItem(row_data["application_date"] or "")

            company_item = QStandardItem(row_data["company_name"] or "")

            role_item = QStandardItem(row_data["role_title"] or "")

            status_label = row_data["status_label"] or ""
            status_item = QStandardItem(status_label)
            status_item.setData(row_data["status_id"], _ROLE_ID)
            if status_label in _STATUS_BG:
                status_item.setBackground(QColor(_STATUS_BG[status_label]))
            if status_label in _STATUS_FG:
                status_item.setForeground(QColor(_STATUS_FG[status_label]))

            phase_label = row_data["phase_label"] or ""
            phase_item = QStandardItem(phase_label)
            phase_item.setData(row_data["phase_id"], _ROLE_ID)
            if phase_label in _PHASE_BG:
                phase_item.setBackground(QColor(_PHASE_BG[phase_label]))
            if phase_label in _PHASE_FG:
                phase_item.setForeground(QColor(_PHASE_FG[phase_label]))

            modified_item = QStandardItem(row_data["updated_at"] or "")

            category_label = row_data["category_label"] or ""
            category_item = QStandardItem(category_label)
            category_item.setData(row_data["category_id"], _ROLE_ID)

            priority = row_data["priority_score"]
            priority_item = QStandardItem(
                str(priority) if priority is not None else ""
            )

            self._source_model.appendRow([
                id_item,
                date_item,
                company_item,
                role_item,
                status_item,
                phase_item,
                modified_item,
                category_item,
                priority_item,
            ])

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._apply_filters()
        self._refresh_empty_state()

    def _apply_filters(self) -> None:
        """Push current filter criteria to the proxy model."""
        self._proxy.set_filters(
            search=self._search_input.text().strip(),
            status_id=self._status_combo.currentData(),
            phase_id=self._phase_combo.currentData(),
            category_id=self._category_combo.currentData(),
        )
        self._update_status_bar()
        self._refresh_empty_state()

    def _refresh_empty_state(self) -> None:
        """Show the empty-state label when no rows are visible."""
        visible = self._proxy.rowCount()
        self._empty_label.setGeometry(self._table.rect())
        self._empty_label.setVisible(visible == 0)
        if visible == 0:
            self._empty_label.raise_()

    def _update_status_bar(self) -> None:
        """Count visible rows, group by status, and update the status bar."""
        status_counts: dict[str, int] = {}
        visible = self._proxy.rowCount()

        for i in range(visible):
            source_idx = self._proxy.mapToSource(self._proxy.index(i, _COL_STATUS))
            item = self._source_model.item(source_idx.row(), _COL_STATUS)
            label = item.text() if item else ""
            if label:
                status_counts[label] = status_counts.get(label, 0) + 1

        if status_counts:
            breakdown = ", ".join(
                f"{count} {label}" for label, count in status_counts.items()
            )
            self._status_label.setText(
                f"{visible} application{'s' if visible != 1 else ''}"
                f" | {breakdown}"
            )
        else:
            self._status_label.setText(
                f"{visible} application{'s' if visible != 1 else ''}"
            )

    def reload_reference_data(self, table_name: str) -> None:
        """Reload filter combos when reference data changes in Settings."""
        if table_name == "ref_statuses":
            current_sid = self._status_combo.currentData()
            self._status_combo.blockSignals(True)
            self._status_combo.clear()
            self._status_combo.addItem("All Statuses", None)
            for item in ref_model.get_all_statuses():
                self._status_combo.addItem(item["label"], item["id"])
            idx = self._status_combo.findData(current_sid)
            self._status_combo.setCurrentIndex(max(idx, 0))
            self._status_combo.blockSignals(False)

        elif table_name == "ref_phases":
            current_pid = self._phase_combo.currentData()
            self._phase_combo.blockSignals(True)
            self._phase_combo.clear()
            self._phase_combo.addItem("All Phases", None)
            for item in ref_model.get_all_phases():
                self._phase_combo.addItem(item["label"], item["id"])
            idx = self._phase_combo.findData(current_pid)
            self._phase_combo.setCurrentIndex(max(idx, 0))
            self._phase_combo.blockSignals(False)

        elif table_name == "ref_categories":
            current_cid = self._category_combo.currentData()
            self._category_combo.blockSignals(True)
            self._category_combo.clear()
            self._category_combo.addItem("All Categories", None)
            for item in ref_model.get_active("ref_categories"):
                self._category_combo.addItem(item["label"], item["id"])
            idx = self._category_combo.findData(current_cid)
            self._category_combo.setCurrentIndex(max(idx, 0))
            self._category_combo.blockSignals(False)

        self._apply_filters()

    # ── Slot handlers ────────────────────────────────────────────────────────

    def _on_add(self) -> None:
        """Open the Add Application dialog; reload table on success."""
        dlg = ApplicationForm(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    def _edit_application(self) -> None:
        """Open the Edit Application dialog for the selected row."""
        application_id = self._selected_application_id()
        if application_id is None:
            QMessageBox.warning(
                self, "No Selection", "Select an application to edit."
            )
            return
        dlg = ApplicationForm(parent=self, application_id=application_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    def _on_delete(self) -> None:
        """Confirm then delete the selected application."""
        application_id = self._selected_application_id()
        if application_id is None:
            QMessageBox.warning(
                self, "No Selection", "Select an application to delete."
            )
            return

        sel_rows = self._table.selectionModel().selectedRows()
        if not sel_rows:
            return
        source_row = self._proxy.mapToSource(sel_rows[0]).row()
        role = (self._source_model.item(source_row, _COL_ROLE) or QStandardItem()).text()
        company = (
            self._source_model.item(source_row, _COL_COMPANY) or QStandardItem()
        ).text()

        dlg = ConfirmDialog(
            f"Delete '{role}' at '{company}'?\n\nThis action cannot be undone.",
            parent=self,
        )
        if dlg.exec() != ConfirmDialog.DialogCode.Accepted:
            return

        try:
            application_model.delete_application(application_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot Delete", str(exc))
            return

        self._load_data()
