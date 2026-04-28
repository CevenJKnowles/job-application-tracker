"""Settings tab: manage reference table data."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import jat.models.reference as ref_model
from jat.gui.dialogs.confirm_dialog import ConfirmDialog

_DISPLAY_TO_TABLE: dict[str, str] = {
    "Phases": "ref_phases",
    "Statuses": "ref_statuses",
    "Categories": "ref_categories",
    "Employment Types": "ref_employment_types",
    "Sources": "ref_sources",
    "Work Modes": "ref_work_modes",
    "Currencies": "ref_currencies",
}

# Tables for which reference_data_changed is emitted after add/remove
_SIGNAL_TABLES = frozenset(
    {"ref_phases", "ref_statuses", "ref_categories", "ref_sources"}
)

_COL_ID = 0
_COL_LABEL = 1
_COL_STATUS = 2
_COL_ORDER = 3
_COL_FUNNEL = 4

_STATUSES_TABLE = "ref_statuses"


class SettingsTab(QWidget):
    """Left-panel table selector; right-panel row editor for ref_ tables."""

    reference_data_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        """Build the split layout."""
        super().__init__(parent)

        root = QHBoxLayout(self)

        # ── Left panel ──────────────────────────────────────────────────────
        self._list = QListWidget()
        self._list.setFixedWidth(200)
        self._list.addItems(_DISPLAY_TO_TABLE.keys())
        self._list.currentTextChanged.connect(self._on_table_selected)
        root.addWidget(self._list)

        # ── Right panel ──────────────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)

        self._heading = QLabel("Select a table from the list.")
        self._heading.setAlignment(Qt.AlignmentFlag.AlignLeft)
        right_layout.addWidget(self._heading)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["ID", "Label", "Status", "Order"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        right_layout.addWidget(self._table)

        # ── Button row ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self._btn_add = QPushButton("Add")
        self._btn_add.clicked.connect(self._on_add)
        btn_row.addWidget(self._btn_add)

        self._btn_edit = QPushButton("Edit")
        self._btn_edit.clicked.connect(self._on_edit)
        btn_row.addWidget(self._btn_edit)

        self._btn_remove = QPushButton("Remove")
        self._btn_remove.clicked.connect(self._on_remove)
        btn_row.addWidget(self._btn_remove)

        self._btn_up = QPushButton("Move Up")
        self._btn_up.clicked.connect(self._on_move_up)
        btn_row.addWidget(self._btn_up)

        self._btn_down = QPushButton("Move Down")
        self._btn_down.clicked.connect(self._on_move_down)
        btn_row.addWidget(self._btn_down)

        right_layout.addLayout(btn_row)

        # ── Funnel button row (ref_statuses only) ────────────────────────────
        self._funnel_row_widget = QWidget()
        funnel_row = QHBoxLayout(self._funnel_row_widget)
        funnel_row.setContentsMargins(0, 0, 0, 0)

        self._btn_set_funnel = QPushButton("Set Funnel Position")
        self._btn_set_funnel.clicked.connect(self._on_set_funnel)
        funnel_row.addWidget(self._btn_set_funnel)

        self._btn_remove_funnel = QPushButton("Remove from Funnel")
        self._btn_remove_funnel.clicked.connect(self._on_remove_funnel)
        funnel_row.addWidget(self._btn_remove_funnel)

        funnel_row.addStretch()

        right_layout.addWidget(self._funnel_row_widget)
        self._funnel_row_widget.setVisible(False)

        root.addWidget(right)

        self._current_table: str | None = None
        self._set_row_buttons_enabled(False)

    # ── Private helpers ──────────────────────────────────────────────────────

    def _set_row_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable buttons that require a selected row."""
        for btn in (self._btn_edit, self._btn_remove, self._btn_up, self._btn_down):
            btn.setEnabled(enabled)
        if self._funnel_row_widget.isVisible():
            self._btn_set_funnel.setEnabled(enabled)
            self._btn_remove_funnel.setEnabled(enabled)

    def _selected_row_index(self) -> int | None:
        """Return the currently selected visual row index, or None."""
        indexes = self._table.selectedIndexes()
        return indexes[0].row() if indexes else None

    def _row_id(self, visual_row: int) -> int:
        """Return the database id stored in the ID column of visual_row."""
        return int(self._table.item(visual_row, _COL_ID).text())

    def _row_is_active(self, visual_row: int) -> bool:
        """Return True if the row's Status cell reads 'Active'."""
        return self._table.item(visual_row, _COL_STATUS).text() == "Active"

    def _refresh(self) -> None:
        """Reload the current table from the model and repopulate the widget."""
        if self._current_table is None:
            return

        is_statuses = self._current_table == _STATUSES_TABLE
        col_count = 5 if is_statuses else 4
        self._table.setColumnCount(col_count)
        headers = ["ID", "Label", "Status", "Order"]
        if is_statuses:
            headers.append("Funnel Position")
        self._table.setHorizontalHeaderLabels(headers)

        rows = ref_model.get_all(self._current_table)
        self._table.setRowCount(0)

        for row_data in rows:
            visual_row = self._table.rowCount()
            self._table.insertRow(visual_row)
            self._table.setItem(visual_row, _COL_ID, QTableWidgetItem(str(row_data["id"])))
            self._table.setItem(visual_row, _COL_LABEL, QTableWidgetItem(row_data["label"]))
            status = "Active" if row_data["is_active"] else "Inactive"
            self._table.setItem(visual_row, _COL_STATUS, QTableWidgetItem(status))
            self._table.setItem(
                visual_row, _COL_ORDER, QTableWidgetItem(str(row_data["sort_order"]))
            )
            if is_statuses:
                funnel_val = row_data.get("funnel_order")
                funnel_text = "" if funnel_val is None else str(funnel_val)
                self._table.setItem(visual_row, _COL_FUNNEL, QTableWidgetItem(funnel_text))

        self._table.resizeColumnsToContents()
        self._set_row_buttons_enabled(False)

    # ── Slot handlers ────────────────────────────────────────────────────────

    def _on_table_selected(self, display_name: str) -> None:
        """Switch the right panel to show data for the selected reference table."""
        self._current_table = _DISPLAY_TO_TABLE.get(display_name)
        self._heading.setText(display_name)
        self._btn_add.setEnabled(self._current_table is not None)
        is_statuses = self._current_table == _STATUSES_TABLE
        self._funnel_row_widget.setVisible(is_statuses)
        self._refresh()

    def _on_row_selected(self) -> None:
        """Update button states when a row is selected."""
        row = self._selected_row_index()
        if row is None:
            self._set_row_buttons_enabled(False)
            return
        self._set_row_buttons_enabled(True)

    def _on_add(self) -> None:
        """Prompt for a new label and insert it into the current table."""
        if self._current_table is None:
            return

        label, ok = QInputDialog.getText(self, "Add", "Label:")
        if not ok or not label.strip():
            return

        ref_model.add_label(self._current_table, label.strip())
        self._refresh()
        if self._current_table in _SIGNAL_TABLES:
            self.reference_data_changed.emit(self._current_table)

    def _on_edit(self) -> None:
        """Prompt with the current label pre-filled and update on confirm."""
        row = self._selected_row_index()
        if row is None or self._current_table is None:
            return

        current_label = self._table.item(row, _COL_LABEL).text()
        new_label, ok = QInputDialog.getText(self, "Edit", "Label:", text=current_label)
        if not ok or not new_label.strip():
            return

        ref_model.update_label(self._current_table, self._row_id(row), new_label.strip())
        self._refresh()

    def _on_remove(self) -> None:
        """Soft-delete (is_active = 0) the selected row after confirmation."""
        row = self._selected_row_index()
        if row is None or self._current_table is None:
            return

        is_active = self._row_is_active(row)
        row_id = self._row_id(row)

        if is_active:
            label = self._table.item(row, _COL_LABEL).text()
            dlg = ConfirmDialog(
                f"Remove '{label}'?\n\nIt will be hidden from all drop-downs.",
                parent=self,
            )
            if dlg.exec() != ConfirmDialog.DialogCode.Accepted:
                return
            ref_model.set_active(self._current_table, row_id, 0)
            if self._current_table in _SIGNAL_TABLES:
                self.reference_data_changed.emit(self._current_table)
        else:
            # Reactivate already-removed row
            ref_model.set_active(self._current_table, row_id, 1)
            if self._current_table in _SIGNAL_TABLES:
                self.reference_data_changed.emit(self._current_table)

        self._refresh()

    def _on_move_up(self) -> None:
        """Swap the selected row with the one above it and persist the new order."""
        row = self._selected_row_index()
        if row is None or row == 0 or self._current_table is None:
            return

        ordered_ids = [self._row_id(r) for r in range(self._table.rowCount())]
        ordered_ids[row - 1], ordered_ids[row] = ordered_ids[row], ordered_ids[row - 1]
        ref_model.reorder(self._current_table, ordered_ids)
        self._refresh()

    def _on_move_down(self) -> None:
        """Swap the selected row with the one below it and persist the new order."""
        row = self._selected_row_index()
        last = self._table.rowCount() - 1
        if row is None or row == last or self._current_table is None:
            return

        ordered_ids = [self._row_id(r) for r in range(self._table.rowCount())]
        ordered_ids[row], ordered_ids[row + 1] = ordered_ids[row + 1], ordered_ids[row]
        ref_model.reorder(self._current_table, ordered_ids)
        self._refresh()

    def _on_set_funnel(self) -> None:
        """Prompt for a funnel position integer and persist it for the selected row."""
        row = self._selected_row_index()
        if row is None:
            return

        value, ok = QInputDialog.getInt(
            self,
            "Funnel Position",
            "Position (1–8):",
            value=1,
            min=1,
            max=8,
        )
        if not ok:
            return

        ref_model.set_funnel_order(self._row_id(row), value)
        self._refresh()

    def _on_remove_funnel(self) -> None:
        """Clear the funnel position for the selected row."""
        row = self._selected_row_index()
        if row is None:
            return

        ref_model.set_funnel_order(self._row_id(row), None)
        self._refresh()
