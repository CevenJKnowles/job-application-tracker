"""Dialog for adding or editing a company record."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

import jat.models.company as company_model
import jat.models.reference as ref_model
from jat.gui.style import COLOURS


def _section_header(title: str) -> QLabel:
    """Return a styled section label."""
    lbl = QLabel(title.upper())
    lbl.setStyleSheet(
        "font-family: monospace; font-size: 10px; letter-spacing: 0.12em;"
        f" color: {COLOURS['muted']};"
        f" border-bottom: 1px solid {COLOURS['border']};"
        " padding-bottom: 4px; margin-top: 8px;"
    )
    lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return lbl


class CompanyForm(QDialog):
    """Add or edit a single company. Pass company_id to enter edit mode."""

    def __init__(self, parent=None, company_id: int | None = None) -> None:
        """Build the form; pre-populate fields when company_id is provided."""
        super().__init__(parent)
        self._company_id = company_id
        self._name_conflict = False

        self.setWindowTitle(
            "Edit Company" if company_id is not None else "Add Company"
        )
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)

        # ── Section: Company Details ──────────────────────────────────────────
        root.addWidget(_section_header("Company Details"))
        form = QGridLayout()
        form.setColumnStretch(1, 1)
        form.setVerticalSpacing(8)

        form.addWidget(QLabel("Company Name *"), 0, 0, Qt.AlignmentFlag.AlignTop)
        self._name_edit = QLineEdit()
        form.addWidget(self._name_edit, 0, 1)

        self._name_warning = QLabel("Company name already exists.")
        self._name_warning.setStyleSheet("color: red;")
        self._name_warning.hide()
        form.addWidget(self._name_warning, 1, 1)

        form.addWidget(QLabel("Industry"), 2, 0)
        ind_w = QWidget()
        ind_row = QHBoxLayout(ind_w)
        ind_row.setContentsMargins(0, 0, 0, 0)
        ind_row.setSpacing(4)
        self._industry_edit = QLineEdit()
        self._industry_completer = QCompleter(
            company_model.get_all_industries(), self._industry_edit
        )
        self._industry_completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self._industry_completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self._industry_edit.setCompleter(self._industry_completer)
        ind_row.addWidget(self._industry_edit)
        ind_plus = QPushButton("+")
        ind_plus.setFixedSize(28, 28)
        ind_plus.setStyleSheet(
            f"QPushButton {{ background: {COLOURS['accent']}; color: white;"
            " border: none; border-radius: 4px; font-size: 14px; }}"
        )
        ind_plus.clicked.connect(self._on_accept_industry)
        ind_row.addWidget(ind_plus)
        form.addWidget(ind_w, 2, 1)

        form.addWidget(QLabel("Website"), 3, 0)
        self._website_edit = QLineEdit()
        form.addWidget(self._website_edit, 3, 1)

        form.addWidget(QLabel("Notes"), 4, 0, Qt.AlignmentFlag.AlignTop)
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(72)
        form.addWidget(self._notes_edit, 4, 1)

        root.addLayout(form)

        # ── Section: Contact ──────────────────────────────────────────────────
        root.addWidget(_section_header("Contact"))
        contact_form = QGridLayout()
        contact_form.setColumnStretch(1, 1)
        contact_form.setVerticalSpacing(8)

        contact_form.addWidget(QLabel("Contact Name"), 0, 0)
        self._contact_name_edit = QLineEdit()
        contact_form.addWidget(self._contact_name_edit, 0, 1)

        contact_form.addWidget(QLabel("Contact Email"), 1, 0)
        self._contact_email_edit = QLineEdit()
        contact_form.addWidget(self._contact_email_edit, 1, 1)

        contact_form.addWidget(QLabel("Phone"), 2, 0)
        phone_w = QWidget()
        phone_row = QHBoxLayout(phone_w)
        phone_row.setContentsMargins(0, 0, 0, 0)
        phone_row.setSpacing(6)
        self._contact_prefix_edit = QLineEdit()
        self._contact_prefix_edit.setFixedWidth(70)
        self._contact_prefix_edit.setPlaceholderText("+49")
        self._contact_number_edit = QLineEdit()
        phone_row.addWidget(self._contact_prefix_edit)
        phone_row.addWidget(self._contact_number_edit)
        contact_form.addWidget(phone_w, 2, 1)

        root.addLayout(contact_form)

        # ── Section: Links ────────────────────────────────────────────────────
        root.addWidget(_section_header("Links"))

        self._links_container = QVBoxLayout()
        self._links_container.setSpacing(4)
        self._link_rows: list[tuple[QComboBox, QLineEdit, QPushButton, int | None]] = []
        root.addLayout(self._links_container)

        self._add_link_btn = QPushButton("+ Add link")
        self._add_link_btn.clicked.connect(lambda: self._add_link_row())
        root.addWidget(self._add_link_btn)

        # ── Buttons ───────────────────────────────────────────────────────────
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

        # Load platform list once for the session
        self._platform_options: list[dict] = ref_model.get_all_link_platforms()

        # Wire signals and pre-populate
        self._existing_names = self._load_existing_names()
        if company_id is not None:
            self._populate(company_id)
        self._name_edit.textChanged.connect(self._on_name_changed)
        self._update_ok_button()

    # ── Private helpers ───────────────────────────────────────────────────────

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
        self._contact_name_edit.setText(row["contact_name"] or "")
        self._contact_email_edit.setText(row["contact_email"] or "")
        self._contact_prefix_edit.setText(row["contact_phone_prefix"] or "")
        self._contact_number_edit.setText(row["contact_phone_number"] or "")

        for link in company_model.get_company_links(company_id):
            self._add_link_row(
                platform_id=link.get("platform_id"),
                url=link["url"],
                link_id=link["link_id"],
            )

    def _platform_items(self) -> list[tuple[str, int | None]]:
        """Return (label, id) pairs for the platform combo including 'Other…' at end."""
        items: list[tuple[str, int | None]] = [
            (p["label"], p["id"]) for p in self._platform_options
        ]
        items.append(("Other…", None))
        return items

    def _add_link_row(
        self,
        platform_id: int | None = None,
        url: str = "",
        link_id: int | None = None,
    ) -> None:
        """Append one platform + URL row to the links section."""
        row_w = QWidget()
        row_layout = QHBoxLayout(row_w)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        platform_combo = QComboBox()
        platform_combo.setFixedWidth(160)
        self._populate_platform_combo(platform_combo)
        if platform_id is not None:
            idx = platform_combo.findData(platform_id)
            if idx >= 0:
                platform_combo.setCurrentIndex(idx)

        platform_combo.currentIndexChanged.connect(
            lambda _idx, cb=platform_combo: self._on_platform_changed(cb)
        )

        url_edit = QLineEdit()
        url_edit.setPlaceholderText("https://…")
        url_edit.setText(url)

        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(28, 28)

        row_layout.addWidget(platform_combo)
        row_layout.addWidget(url_edit, 1)
        row_layout.addWidget(remove_btn)

        entry = (platform_combo, url_edit, remove_btn, link_id)
        self._link_rows.append(entry)
        self._links_container.addWidget(row_w)

        remove_btn.clicked.connect(lambda: self._remove_link_row(entry, row_w))

    def _populate_platform_combo(self, combo: QComboBox) -> None:
        """Fill a platform combo from current _platform_options plus 'Other…'."""
        combo.blockSignals(True)
        current_data = combo.currentData()
        combo.clear()
        for label, pid in self._platform_items():
            combo.addItem(label, pid)
        if current_data is not None:
            idx = combo.findData(current_data)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def _on_platform_changed(self, combo: QComboBox) -> None:
        """Handle 'Other…' selection: prompt for custom label and add to ref table."""
        if combo.currentData() is not None:
            return
        if combo.currentText() != "Other…":
            return

        label, ok = QInputDialog.getText(
            self, "Custom Platform", "Platform name:"
        )
        if not ok or not label.strip():
            # Revert to first option
            combo.setCurrentIndex(0)
            return

        new_id = ref_model.add_link_platform(label.strip())
        # Refresh cached options
        self._platform_options = ref_model.get_all_link_platforms()
        # Re-populate all combos and select the new one
        for cb, _url, _btn, _lid in self._link_rows:
            self._populate_platform_combo(cb)
        idx = combo.findData(new_id)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _remove_link_row(
        self,
        entry: tuple[QComboBox, QLineEdit, QPushButton, int | None],
        row_w: QWidget,
    ) -> None:
        """Remove a link row from the UI (DB deletion happens on save)."""
        if entry in self._link_rows:
            self._link_rows.remove(entry)
        row_w.setParent(None)
        row_w.deleteLater()

    def _on_accept_industry(self) -> None:
        """Accept the currently typed industry value and refresh the completer."""
        value = self._industry_edit.text().strip()
        if not value:
            return
        # Refresh completer from DB (the save will persist it)
        all_industries = company_model.get_all_industries()
        if value not in all_industries:
            all_industries.append(value)
            all_industries.sort()
        self._industry_completer = QCompleter(all_industries, self._industry_edit)
        self._industry_completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self._industry_completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self._industry_edit.setCompleter(self._industry_completer)

    def _on_name_changed(self, text: str) -> None:
        """Update conflict flag and warning on every keystroke."""
        self._name_conflict = text.strip().lower() in self._existing_names
        self._name_warning.setVisible(self._name_conflict)
        self._update_ok_button()

    def _update_ok_button(self) -> None:
        """Disable OK when name is empty or conflicts."""
        name_filled = bool(self._name_edit.text().strip())
        self._ok_btn.setEnabled(name_filled and not self._name_conflict)

    # ── Slot handlers ─────────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        """Persist form data; keep dialog open on error."""
        name = self._name_edit.text().strip()
        industry = self._industry_edit.text().strip()
        website = self._website_edit.text().strip()
        notes = self._notes_edit.toPlainText().strip()
        contact_name = self._contact_name_edit.text().strip()
        contact_email = self._contact_email_edit.text().strip()
        contact_phone_prefix = self._contact_prefix_edit.text().strip()
        contact_phone_number = self._contact_number_edit.text().strip()

        try:
            if self._company_id is None:
                saved_id = company_model.add_company(
                    name,
                    industry,
                    website,
                    notes,
                    contact_name,
                    contact_email,
                    contact_phone_prefix,
                    contact_phone_number,
                )
            else:
                company_model.update_company(
                    self._company_id,
                    name,
                    industry,
                    website,
                    notes,
                    contact_name,
                    contact_email,
                    contact_phone_prefix,
                    contact_phone_number,
                )
                saved_id = self._company_id
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return

        self._save_links(saved_id)
        # Refresh industry completer after save so the new value appears next time
        all_industries = company_model.get_all_industries()
        self._industry_completer = QCompleter(all_industries, self._industry_edit)
        self._industry_completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self._industry_edit.setCompleter(self._industry_completer)
        self.accept()

    def _save_links(self, company_id: int) -> None:
        """Persist all current link rows: delete existing and re-add all."""
        for link in company_model.get_company_links(company_id):
            company_model.delete_company_link(link["link_id"])

        for platform_combo, url_edit, _btn, _lid in self._link_rows:
            platform_id = platform_combo.currentData()
            url = url_edit.text().strip()
            if platform_id is not None and url:
                company_model.add_company_link(company_id, platform_id, url)
