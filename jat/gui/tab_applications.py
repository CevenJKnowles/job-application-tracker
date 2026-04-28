"""Applications tab: browse, search, and manage application records."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
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

import jat.models.application as application_model
import jat.models.reference as ref_model
from jat.gui.dialogs.application_form import ApplicationForm
from jat.gui.dialogs.confirm_dialog import ConfirmDialog

# Hidden ID column + visible columns in display order
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

_STATUS_BG: dict[str, str] = {
    "Reviewing": "#F9E79F",
    "Offer": "#27AE60",
    "Rejected": "#F1948A",
    "Withdrawn": "#D5D8DC",
    "Ghosted": "#F0B27A",
}
_STATUS_FG: dict[str, str] = {
    "Offer": "#FFFFFF",
}

_PHASE_BG: dict[str, str] = {
    "Applied": "#AED6F1",
    "Interview #1": "#A9DFBF",
    "Interview #2": "#A9DFBF",
    "Interview #3": "#A9DFBF",
    "Final Stage": "#76D7C4",
}


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
        for item in ref_model.get_active("ref_statuses"):
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

        # ── Table ────────────────────────────────────────────────────────────
        self._table = QTableWidget(0, _NUM_COLS)
        self._table.setHorizontalHeaderLabels(
            [
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
        )
        self._table.setColumnHidden(_COL_ID, True)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
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
        indexes = self._table.selectedIndexes()
        if not indexes:
            return None
        return int(self._table.item(indexes[0].row(), _COL_ID).text())

    def _load_data(self) -> None:
        """Fetch all applications from the model and repopulate the table."""
        rows = application_model.get_all_applications()
        self._table.setRowCount(0)

        for row_data in rows:
            visual = self._table.rowCount()
            self._table.insertRow(visual)

            self._table.setItem(
                visual, _COL_ID,
                QTableWidgetItem(str(row_data["application_id"])),
            )
            self._table.setItem(
                visual, _COL_DATE_APPLIED,
                QTableWidgetItem(row_data["application_date"] or ""),
            )
            self._table.setItem(
                visual, _COL_COMPANY,
                QTableWidgetItem(row_data["company_name"] or ""),
            )
            self._table.setItem(
                visual, _COL_ROLE,
                QTableWidgetItem(row_data["role_title"] or ""),
            )

            # Status — with colour coding
            status_label = row_data["status_label"] or ""
            status_item = QTableWidgetItem(status_label)
            status_item.setData(Qt.ItemDataRole.UserRole, row_data["status_id"])
            if status_label in _STATUS_BG:
                status_item.setBackground(QColor(_STATUS_BG[status_label]))
            if status_label in _STATUS_FG:
                status_item.setForeground(QColor(_STATUS_FG[status_label]))
            self._table.setItem(visual, _COL_STATUS, status_item)

            # Phase — with colour coding
            phase_label = row_data["phase_label"] or ""
            phase_item = QTableWidgetItem(phase_label)
            phase_item.setData(Qt.ItemDataRole.UserRole, row_data["phase_id"])
            if phase_label in _PHASE_BG:
                phase_item.setBackground(QColor(_PHASE_BG[phase_label]))
            self._table.setItem(visual, _COL_PHASE, phase_item)

            self._table.setItem(
                visual, _COL_DATE_MODIFIED,
                QTableWidgetItem(row_data["updated_at"] or ""),
            )

            category_item = QTableWidgetItem(row_data["category_label"] or "")
            category_item.setData(
                Qt.ItemDataRole.UserRole, row_data["category_id"]
            )
            self._table.setItem(visual, _COL_CATEGORY, category_item)

            priority = row_data["priority_score"]
            self._table.setItem(
                visual, _COL_PRIORITY,
                QTableWidgetItem(str(priority) if priority is not None else ""),
            )

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._apply_filters()
        self._refresh_empty_state()

    def _apply_filters(self) -> None:
        """Hide rows that don't match the active search/status/phase/category."""
        search = self._search_input.text().strip().lower()
        status_id = self._status_combo.currentData()
        phase_id = self._phase_combo.currentData()
        category_id = self._category_combo.currentData()

        for row in range(self._table.rowCount()):
            company_text = (
                self._table.item(row, _COL_COMPANY) or QTableWidgetItem("")
            ).text().lower()
            role_text = (
                self._table.item(row, _COL_ROLE) or QTableWidgetItem("")
            ).text().lower()

            matches_search = (
                not search
                or search in company_text
                or search in role_text
            )

            if status_id is None:
                matches_status = True
            else:
                item = self._table.item(row, _COL_STATUS)
                row_sid = item.data(Qt.ItemDataRole.UserRole) if item else None
                matches_status = row_sid == status_id

            if phase_id is None:
                matches_phase = True
            else:
                item = self._table.item(row, _COL_PHASE)
                row_pid = item.data(Qt.ItemDataRole.UserRole) if item else None
                matches_phase = row_pid == phase_id

            if category_id is None:
                matches_category = True
            else:
                item = self._table.item(row, _COL_CATEGORY)
                row_cid = item.data(Qt.ItemDataRole.UserRole) if item else None
                matches_category = row_cid == category_id

            self._table.setRowHidden(
                row,
                not (
                    matches_search
                    and matches_status
                    and matches_phase
                    and matches_category
                ),
            )

        self._update_status_bar()
        self._refresh_empty_state()

    def _refresh_empty_state(self) -> None:
        """Show the empty-state label when no rows are visible."""
        visible = sum(
            1
            for r in range(self._table.rowCount())
            if not self._table.isRowHidden(r)
        )
        self._empty_label.setGeometry(self._table.rect())
        self._empty_label.setVisible(visible == 0)
        if visible == 0:
            self._empty_label.raise_()

    def _update_status_bar(self) -> None:
        """Count visible rows, group by status, and update the status bar."""
        status_counts: dict[str, int] = {}
        visible = 0

        for row in range(self._table.rowCount()):
            if self._table.isRowHidden(row):
                continue
            visible += 1
            item = self._table.item(row, _COL_STATUS)
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

        row_index = self._table.selectedIndexes()[0].row()
        role = (
            self._table.item(row_index, _COL_ROLE) or QTableWidgetItem("")
        ).text()
        company = (
            self._table.item(row_index, _COL_COMPANY) or QTableWidgetItem("")
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
