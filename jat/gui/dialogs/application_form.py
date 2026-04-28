"""Dialog for adding or editing a job application."""

from __future__ import annotations

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import jat.models.application as app_model
import jat.models.company as company_model
import jat.models.reference as ref_model
from jat.gui.dialogs.company_form import CompanyForm
from jat.gui.style import COLOURS
from jat.gui.widgets.chip_selector import ChipSelector
from jat.gui.widgets.segmented_toggle import SegmentedToggle

try:
    from babel.numbers import get_currency_name as _babel_currency_name

    def _fmt_currency(code: str) -> str:
        """Return 'EUR — Euro' style label."""
        try:
            return f"{code} — {_babel_currency_name(code, locale='en')}"
        except Exception:
            return code

except ImportError:

    def _fmt_currency(code: str) -> str:  # type: ignore[misc]
        """Fallback: return bare currency code."""
        return code


_PHASE_COLORS: dict[str, str] = {
    "Applied": "#4f7cff",
    "Interview #1": "#3ecf8e",
    "Interview #2": "#3ecf8e",
    "Interview #3": "#3ecf8e",
    "Final Stage": "#f5a623",
}

_STATUS_COLORS: dict[str, str] = {
    "Reviewing": "#a78bfa",
    "Rejected": "#e05252",
    "Withdrawn": "#5a6180",
    "Offer": "#22d3a5",
    "Ghosted": "#4b5563",
}

_EMPLOYMENT_COLORS: dict[str, str] = {}

_CURRENCY_FAVES = ["EUR", "GBP", "USD", "CHF"]


def _section_header(title: str) -> QLabel:
    """Return a styled monospace uppercase section label with border-bottom."""
    lbl = QLabel(title.upper())
    lbl.setStyleSheet(
        "font-family: monospace; font-size: 10px; letter-spacing: 0.12em;"
        f" color: {COLOURS['muted']};"
        f" border-bottom: 1px solid {COLOURS['border']};"
        " padding-bottom: 4px; margin-top: 8px;"
    )
    lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return lbl


class ApplicationForm(QDialog):
    """Add or edit a single application. Pass application_id for edit mode."""

    def __init__(self, parent=None, application_id: int | None = None) -> None:
        """Build the scrollable form; pre-populate when application_id is given."""
        super().__init__(parent)
        self._application_id = application_id

        title = "Edit Application" if application_id is not None else "Add Application"
        self.setWindowTitle(title)
        self.setMinimumSize(620, 700)

        root = QVBoxLayout(self)
        root.setSpacing(8)

        # ── Scrollable content area ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        content = QVBoxLayout(container)
        content.setSpacing(4)
        content.setContentsMargins(12, 8, 12, 8)
        scroll.setWidget(container)

        # Preload reference data
        self._load_ref_data()

        # ── Section: Core Details ─────────────────────────────────────────────
        content.addWidget(_section_header("Core Details"))
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.setVerticalSpacing(8)
        row = 0

        grid.addWidget(QLabel("Company *"), row, 0)
        company_w = QWidget()
        company_row = QHBoxLayout(company_w)
        company_row.setContentsMargins(0, 0, 0, 0)
        company_row.setSpacing(6)
        self._company_edit = QLineEdit()
        self._company_edit.setPlaceholderText("Type to search...")
        company_row.addWidget(self._company_edit)
        self._company_add_btn = QPushButton("+")
        self._company_add_btn.setFixedSize(36, 36)
        self._company_add_btn.setStyleSheet(
            f"QPushButton {{ background: {COLOURS['accent']}; color: white;"
            " border: none; border-radius: 4px; font-size: 18px; }}"
        )
        self._company_add_btn.clicked.connect(self._on_add_company)
        company_row.addWidget(self._company_add_btn)
        grid.addWidget(company_w, row, 1)
        row += 1

        grid.addWidget(QLabel("Role Title *"), row, 0)
        self._role_title = QLineEdit()
        grid.addWidget(self._role_title, row, 1)
        row += 1

        grid.addWidget(QLabel("Application Date *"), row, 0)
        self._application_date = QDateEdit()
        self._application_date.setCalendarPopup(True)
        self._application_date.setDate(QDate.currentDate())
        grid.addWidget(self._application_date, row, 1)
        row += 1

        grid.addWidget(QLabel("Response Date"), row, 0)
        resp_w = QWidget()
        resp_row = QHBoxLayout(resp_w)
        resp_row.setContentsMargins(0, 0, 0, 0)
        self._response_date_check = QCheckBox("Enable")
        self._response_date = QDateEdit()
        self._response_date.setCalendarPopup(True)
        self._response_date.setDate(QDate.currentDate())
        self._response_date.setEnabled(False)
        self._response_date_check.toggled.connect(self._response_date.setEnabled)
        resp_row.addWidget(self._response_date_check)
        resp_row.addWidget(self._response_date)
        grid.addWidget(resp_w, row, 1)
        row += 1

        content.addLayout(grid)

        # ── Section: Classification ───────────────────────────────────────────
        content.addWidget(_section_header("Classification"))
        cls_grid = QGridLayout()
        cls_grid.setColumnStretch(1, 1)
        cls_grid.setVerticalSpacing(8)
        row = 0

        cls_grid.addWidget(
            QLabel("Phase *"), row, 0, Qt.AlignmentFlag.AlignTop
        )
        phase_labels = [p["label"] for p in ref_model.get_all_phases()]
        self._phase_chip = ChipSelector(phase_labels, _PHASE_COLORS)
        cls_grid.addWidget(self._phase_chip, row, 1)
        row += 1

        cls_grid.addWidget(
            QLabel("Status"), row, 0, Qt.AlignmentFlag.AlignTop
        )
        status_rows = ref_model.get_active("ref_statuses")
        status_labels = [s["label"] for s in status_rows]
        self._status_chip = ChipSelector(status_labels, _STATUS_COLORS)
        cls_grid.addWidget(self._status_chip, row, 1)
        row += 1

        cls_grid.addWidget(
            QLabel("Employment Type"), row, 0, Qt.AlignmentFlag.AlignTop
        )
        emp_rows = ref_model.get_active("ref_employment_types")
        emp_labels = [e["label"] for e in emp_rows]
        self._employment_chip = ChipSelector(emp_labels, _EMPLOYMENT_COLORS)
        cls_grid.addWidget(self._employment_chip, row, 1)
        row += 1

        cls_grid.addWidget(QLabel("Category"), row, 0)
        self._category_edit = QLineEdit()
        cat_completer = QCompleter(
            [c["label"] for c in ref_model.get_active("ref_categories")]
        )
        cat_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        cat_completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self._category_edit.setCompleter(cat_completer)
        cls_grid.addWidget(self._category_edit, row, 1)
        row += 1

        cls_grid.addWidget(QLabel("Source"), row, 0)
        self._source_edit = QLineEdit()
        src_completer = QCompleter(
            [s["label"] for s in ref_model.get_active("ref_sources")]
        )
        src_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        src_completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self._source_edit.setCompleter(src_completer)
        cls_grid.addWidget(self._source_edit, row, 1)
        row += 1

        content.addLayout(cls_grid)

        # ── Section: Location & Mode ──────────────────────────────────────────
        content.addWidget(_section_header("Location & Mode"))
        loc_grid = QGridLayout()
        loc_grid.setColumnStretch(1, 1)
        loc_grid.setVerticalSpacing(8)
        row = 0

        loc_grid.addWidget(
            QLabel("Work Mode"), row, 0, Qt.AlignmentFlag.AlignTop
        )
        wm_labels = [w["label"] for w in ref_model.get_active("ref_work_modes")]
        self._work_mode_toggle = SegmentedToggle(wm_labels)
        loc_grid.addWidget(self._work_mode_toggle, row, 1)
        row += 1

        loc_grid.addWidget(QLabel("City"), row, 0)
        self._city = QLineEdit()
        loc_grid.addWidget(self._city, row, 1)
        row += 1

        loc_grid.addWidget(QLabel("Country"), row, 0)
        self._country = QLineEdit()
        loc_grid.addWidget(self._country, row, 1)
        row += 1

        content.addLayout(loc_grid)

        # ── Section: Compensation ─────────────────────────────────────────────
        content.addWidget(_section_header("Compensation"))
        comp_grid = QGridLayout()
        comp_grid.setColumnStretch(1, 1)
        comp_grid.setVerticalSpacing(8)
        row = 0

        # Currency favourites + completer
        comp_grid.addWidget(
            QLabel("Currency"), row, 0, Qt.AlignmentFlag.AlignTop
        )
        curr_w = QWidget()
        curr_v = QVBoxLayout(curr_w)
        curr_v.setContentsMargins(0, 0, 0, 0)
        curr_v.setSpacing(4)

        fave_w = QWidget()
        fave_row = QHBoxLayout(fave_w)
        fave_row.setContentsMargins(0, 0, 0, 0)
        fave_row.setSpacing(4)
        self._currency_fave_btns: dict[str, QToolButton] = {}
        for code in _CURRENCY_FAVES:
            btn = QToolButton()
            btn.setText(code)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda _c, c=code: self._on_currency_fave(c))
            self._currency_fave_btns[code] = btn
            fave_row.addWidget(btn)
        fave_row.addStretch()
        curr_v.addWidget(fave_w)

        self._currency_edit = QLineEdit()
        self._currency_edit.setPlaceholderText("Currency…")
        cur_items = [
            _fmt_currency(r["label"])
            for r in ref_model.get_active("ref_currencies")
        ]
        cur_completer = QCompleter(cur_items)
        cur_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        cur_completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        cur_completer.activated.connect(self._on_currency_activated)
        self._currency_edit.setCompleter(cur_completer)
        self._currency_edit.textEdited.connect(self._on_currency_text_edited)
        curr_v.addWidget(self._currency_edit)
        comp_grid.addWidget(curr_w, row, 1)
        row += 1

        self._selected_currency_code: str | None = None
        self._apply_currency_styles()

        comp_grid.addWidget(QLabel("Salary"), row, 0)
        sal_w = QWidget()
        sal_row = QHBoxLayout(sal_w)
        sal_row.setContentsMargins(0, 0, 0, 0)
        sal_row.setSpacing(8)
        sal_row.addWidget(QLabel("Min"))
        self._salary_min = QLineEdit()
        self._salary_min.setPlaceholderText("0.00")
        sal_row.addWidget(self._salary_min)
        sal_row.addWidget(QLabel("Max"))
        self._salary_max = QLineEdit()
        self._salary_max.setPlaceholderText("0.00")
        sal_row.addWidget(self._salary_max)
        comp_grid.addWidget(sal_w, row, 1)
        row += 1

        content.addLayout(comp_grid)

        # ── Section: Meta ─────────────────────────────────────────────────────
        content.addWidget(_section_header("Meta"))
        meta_grid = QGridLayout()
        meta_grid.setColumnStretch(1, 1)
        meta_grid.setVerticalSpacing(8)
        row = 0

        meta_grid.addWidget(QLabel("Priority"), row, 0)
        self._priority_value = 3
        prio_w = QWidget()
        prio_row = QHBoxLayout(prio_w)
        prio_row.setContentsMargins(0, 0, 0, 0)
        prio_row.setSpacing(6)
        self._priority_minus = QPushButton("−")
        self._priority_minus.setFixedSize(28, 28)
        self._priority_minus.clicked.connect(self._on_priority_minus)
        self._priority_label = QLabel("3")
        self._priority_label.setFixedWidth(24)
        self._priority_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._priority_plus = QPushButton("+")
        self._priority_plus.setFixedSize(28, 28)
        self._priority_plus.clicked.connect(self._on_priority_plus)
        prio_row.addWidget(self._priority_minus)
        prio_row.addWidget(self._priority_label)
        prio_row.addWidget(self._priority_plus)
        prio_row.addStretch()
        meta_grid.addWidget(prio_w, row, 1)
        row += 1

        meta_grid.addWidget(QLabel("Follow-up Date"), row, 0)
        fup_w = QWidget()
        fup_row = QHBoxLayout(fup_w)
        fup_row.setContentsMargins(0, 0, 0, 0)
        self._follow_up_check = QCheckBox("Enable")
        self._follow_up_date = QDateEdit()
        self._follow_up_date.setCalendarPopup(True)
        self._follow_up_date.setDate(QDate.currentDate())
        self._follow_up_date.setEnabled(False)
        self._follow_up_check.toggled.connect(self._follow_up_date.setEnabled)
        fup_row.addWidget(self._follow_up_check)
        fup_row.addWidget(self._follow_up_date)
        meta_grid.addWidget(fup_w, row, 1)
        row += 1

        meta_grid.addWidget(QLabel("Job Posting URL"), row, 0)
        self._job_posting_url = QLineEdit()
        meta_grid.addWidget(self._job_posting_url, row, 1)
        row += 1

        meta_grid.addWidget(
            QLabel("Notes"), row, 0, Qt.AlignmentFlag.AlignTop
        )
        self._notes = QTextEdit()
        self._notes.setFixedHeight(80)
        meta_grid.addWidget(self._notes, row, 1)
        row += 1

        content.addLayout(meta_grid)
        content.addStretch()

        root.addWidget(scroll)

        # ── Buttons ───────────────────────────────────────────────────────────
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

        # Load company names into completer and populate if editing
        self._refresh_company_completer()
        if application_id is not None:
            self._populate(application_id)

    # ── Private: reference data maps ─────────────────────────────────────────

    def _load_ref_data(self) -> None:
        """Build label→id maps for all reference tables used in this form."""
        self._phase_map: dict[str, int] = {}
        for r in ref_model.get_all_phases():
            self._phase_map[r["label"]] = r["id"]

        self._status_map: dict[str, int] = {}
        for r in ref_model.get_active("ref_statuses"):
            self._status_map[r["label"]] = r["id"]

        self._employment_map: dict[str, int] = {}
        for r in ref_model.get_active("ref_employment_types"):
            self._employment_map[r["label"]] = r["id"]

        self._category_map: dict[str, int] = {}
        for r in ref_model.get_active("ref_categories"):
            self._category_map[r["label"].lower()] = r["id"]

        self._source_map: dict[str, int] = {}
        for r in ref_model.get_active("ref_sources"):
            self._source_map[r["label"].lower()] = r["id"]

        self._work_mode_map: dict[str, int] = {}
        for r in ref_model.get_active("ref_work_modes"):
            self._work_mode_map[r["label"]] = r["id"]

        self._currency_map: dict[str, int] = {}
        for r in ref_model.get_active("ref_currencies"):
            self._currency_map[r["label"]] = r["id"]

    def _refresh_company_completer(self) -> None:
        """Reload company names from DB and rebuild the completer and map."""
        companies = company_model.get_all_companies()
        self._company_map: dict[str, int] = {
            c["company_name"].lower(): c["id"] for c in companies
        }
        names = [c["company_name"] for c in companies]
        completer = QCompleter(names, self._company_edit)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._company_edit.setCompleter(completer)

    # ── Private: populate for edit mode ──────────────────────────────────────

    def _populate(self, application_id: int) -> None:
        """Fill all widgets from an existing application record."""
        record = app_model.get_application_by_id(application_id)
        if record is None:
            return

        self._company_edit.setText(record["company_name"] or "")
        self._role_title.setText(record["role_title"] or "")

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

        if record["phase_label"]:
            self._phase_chip.set_selected(record["phase_label"])
        if record["status_label"]:
            self._status_chip.set_selected(record["status_label"])
        if record["employment_type_label"]:
            self._employment_chip.set_selected(record["employment_type_label"])
        if record["category_label"]:
            self._category_edit.setText(record["category_label"])
        if record["source_label"]:
            self._source_edit.setText(record["source_label"])
        if record["work_mode_label"]:
            self._work_mode_toggle.set_selected(record["work_mode_label"])

        currency_code = record["currency_label"]
        if currency_code:
            self._selected_currency_code = currency_code
            self._currency_edit.setText(_fmt_currency(currency_code))
            self._apply_currency_styles()

        if record["salary_min"] is not None:
            self._salary_min.setText(str(record["salary_min"]))
        if record["salary_max"] is not None:
            self._salary_max.setText(str(record["salary_max"]))

        if record["priority_score"] is not None:
            self._priority_value = int(record["priority_score"])
            self._priority_label.setText(str(self._priority_value))

        if record["follow_up_date"]:
            self._follow_up_check.setChecked(True)
            self._follow_up_date.setEnabled(True)
            self._follow_up_date.setDate(
                QDate.fromString(record["follow_up_date"], "yyyy-MM-dd")
            )
        self._job_posting_url.setText(record["job_posting_url"] or "")
        self._notes.setPlainText(record["notes"] or "")

    # ── Private: currency helpers ─────────────────────────────────────────────

    def _on_currency_fave(self, code: str) -> None:
        """Select a currency favourite button."""
        if self._selected_currency_code == code:
            self._selected_currency_code = None
            self._currency_edit.clear()
        else:
            self._selected_currency_code = code
            self._currency_edit.setText(_fmt_currency(code))
        self._apply_currency_styles()

    def _on_currency_activated(self, text: str) -> None:
        """Parse a completer selection like 'EUR — Euro' to set the currency code."""
        code = text.split(" — ")[0].strip() if " — " in text else text.strip()[:3]
        code = code.upper()
        if code in self._currency_map:
            self._selected_currency_code = code
            self._apply_currency_styles()

    def _on_currency_text_edited(self, text: str) -> None:
        """Update selected currency when the user types directly."""
        code = text.strip()[:3].upper()
        if code in self._currency_map and (
            len(text.strip()) == 3 or " — " in text
        ):
            self._selected_currency_code = code
        else:
            self._selected_currency_code = None
        self._apply_currency_styles()

    def _apply_currency_styles(self) -> None:
        """Restyle the four favourite buttons based on selected currency."""
        active_color = COLOURS["green"]
        for code, btn in self._currency_fave_btns.items():
            if code == self._selected_currency_code:
                btn.setStyleSheet(
                    f"QToolButton {{ background: rgba(62,207,142,0.12);"
                    f" border: 1px solid {active_color};"
                    f" color: {active_color};"
                    f" padding: 4px 10px; border-radius: 4px; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QToolButton {{ background: transparent;"
                    f" border: 1px solid {COLOURS['border']};"
                    f" color: {COLOURS['muted']};"
                    f" padding: 4px 10px; border-radius: 4px; }}"
                )

    # ── Private: priority stepper ─────────────────────────────────────────────

    def _on_priority_minus(self) -> None:
        """Decrease priority, clamped to 1."""
        self._priority_value = max(1, self._priority_value - 1)
        self._priority_label.setText(str(self._priority_value))

    def _on_priority_plus(self) -> None:
        """Increase priority, clamped to 5."""
        self._priority_value = min(5, self._priority_value + 1)
        self._priority_label.setText(str(self._priority_value))

    # ── Private: company add button ───────────────────────────────────────────

    def _on_add_company(self) -> None:
        """Open CompanyForm and refresh the completer on success."""
        old_ids = set(self._company_map.values())
        dlg = CompanyForm(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_company_completer()
            new_id = next(
                (v for v in self._company_map.values() if v not in old_ids),
                None,
            )
            if new_id is not None:
                new_name = next(
                    (k for k, v in self._company_map.items() if v == new_id),
                    None,
                )
                if new_name:
                    self._company_edit.setText(
                        next(
                            c["company_name"]
                            for c in company_model.get_all_companies()
                            if c["id"] == new_id
                        )
                    )

    # ── Private: validation helpers ───────────────────────────────────────────

    def _resolve_id(self, label: str, mapping: dict[str, int]) -> int | None:
        """Case-insensitive label → id lookup; returns None if not found."""
        return mapping.get(label.lower())

    # ── Slot: accept ──────────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        """Validate all required fields, collect values, and persist."""
        # ── Resolve required fields ──────────────────────────────────────────
        company_name = self._company_edit.text().strip()
        company_id = self._company_map.get(company_name.lower())
        role_title = self._role_title.text().strip()
        application_date = self._application_date.date().toString("yyyy-MM-dd")
        phase_label = self._phase_chip.get_selected()
        phase_id = self._phase_map.get(phase_label) if phase_label else None

        errors: list[str] = []
        if not company_name or company_id is None:
            errors.append("Company is required (must match an existing company).")
        if not role_title:
            errors.append("Role Title is required.")
        if not application_date:
            errors.append("Application Date is required.")
        if phase_id is None:
            errors.append("Phase is required.")
        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return

        # ── URL validation ────────────────────────────────────────────────────
        url = self._job_posting_url.text().strip()
        if url and not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "Job posting URL must start with http:// or https://.",
            )
            return

        # ── Resolve optional IDs ──────────────────────────────────────────────
        status_label = self._status_chip.get_selected()
        status_id = self._status_map.get(status_label) if status_label else None

        emp_label = self._employment_chip.get_selected()
        employment_type_id = (
            self._employment_map.get(emp_label) if emp_label else None
        )

        category_text = self._category_edit.text().strip()
        category_id = self._resolve_id(category_text, self._category_map) \
            if category_text else None

        source_text = self._source_edit.text().strip()
        source_id = self._resolve_id(source_text, self._source_map) \
            if source_text else None

        wm_label = self._work_mode_toggle.get_selected()
        work_mode_id = self._work_mode_map.get(wm_label) if wm_label else None

        currency_id = (
            self._currency_map.get(self._selected_currency_code)
            if self._selected_currency_code
            else None
        )

        def _parse_salary(text: str) -> float | None:
            t = text.strip()
            if not t:
                return None
            try:
                v = float(t)
                return v if v > 0 else None
            except ValueError:
                return None

        salary_min = _parse_salary(self._salary_min.text())
        salary_max = _parse_salary(self._salary_max.text())

        kwargs: dict = {
            "phase_id": phase_id,
            "status_id": status_id,
            "category_id": category_id,
            "employment_type_id": employment_type_id,
            "source_id": source_id,
            "work_mode_id": work_mode_id,
            "currency_id": currency_id,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "priority_score": self._priority_value,
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
            "notes": self._notes.toPlainText().strip() or None,
        }

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
            QMessageBox.warning(self, "Save Error", str(exc))
            return

        self.accept()
