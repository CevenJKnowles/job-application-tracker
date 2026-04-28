"""Reusable segmented toggle widget for the JAT GUI."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from jat.gui.style import COLOURS

_SEG_BASE = "padding: 5px 14px; font-size: 12px;"


class SegmentedToggle(QWidget):
    """Single-select joined button bar with shared outer border-radius."""

    selection_changed = pyqtSignal(str)

    def __init__(self, options: list[str], parent=None) -> None:
        """Build one segment button per option."""
        super().__init__(parent)
        self._options = list(options)
        self._selected: str | None = None
        self._buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        for label in options:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda _checked, lbl=label: self._on_click(lbl))
            self._buttons[label] = btn
            layout.addWidget(btn)

        layout.addStretch()
        self._apply_styles()

    # ── Public API ────────────────────────────────────────────────────────────

    def get_selected(self) -> str | None:
        """Return the currently selected label, or None."""
        return self._selected

    def set_selected(self, label: str) -> None:
        """Select the segment for label; no-op if label is not in options."""
        if label in self._buttons:
            self._selected = label
            self._apply_styles()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _on_click(self, label: str) -> None:
        """Select the clicked segment and emit the signal."""
        self._selected = label
        self._apply_styles()
        self.selection_changed.emit(label)

    def _apply_styles(self) -> None:
        """Restyle all segments, rounding only the outer corners."""
        n = len(self._options)
        for i, label in enumerate(self._options):
            btn = self._buttons[label]
            is_first = i == 0
            is_last = i == n - 1

            if is_first and is_last:
                radius = "border-radius: 7px;"
            elif is_first:
                radius = "border-radius: 7px 0 0 7px;"
            elif is_last:
                radius = "border-radius: 0 7px 7px 0;"
            else:
                radius = "border-radius: 0;"

            # Non-first buttons omit the left border to avoid double lines.
            left_border = (
                f"border-left: 1px solid;"
                if is_first
                else "border-left: none;"
            )

            if label == self._selected:
                border_color = COLOURS["accent"]
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f" background: {COLOURS['accent_lo']};"
                    f" border: 1px solid {border_color};"
                    f" {left_border}"
                    f" color: {border_color};"
                    f" {_SEG_BASE} {radius}"
                    f"}}"
                )
            else:
                border_color = COLOURS["border"]
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f" background: transparent;"
                    f" border: 1px solid {border_color};"
                    f" {left_border}"
                    f" color: {COLOURS['muted']};"
                    f" {_SEG_BASE} {radius}"
                    f"}}"
                )
