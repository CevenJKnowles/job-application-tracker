"""Reusable chip-selector widget for the JAT GUI."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from jat.gui.style import COLOURS

_CHIP_BASE = (
    "padding: 5px 11px; border-radius: 20px; font-size: 12px;"
)


def _hex_to_rgb(hex_color: str) -> str:
    """Convert '#rrggbb' to 'r, g, b' for use in rgba()."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"


class ChipSelector(QWidget):
    """Single-select row of styled push-button chips.

    Clicking the active chip deselects it, allowing the field to be cleared
    (useful for optional selections like Status or Employment Type).
    """

    selection_changed = pyqtSignal(str)

    def __init__(
        self,
        options: list[str],
        color_map: dict[str, str] | None = None,
        parent=None,
    ) -> None:
        """Build chip buttons for each option string."""
        super().__init__(parent)
        self._options = options
        self._color_map: dict[str, str] = color_map or {}
        self._selected: str | None = None
        self._buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for label in options:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setCursor(btn.cursor())
            btn.clicked.connect(lambda _checked, lbl=label: self._on_click(lbl))
            self._buttons[label] = btn
            layout.addWidget(btn)

        layout.addStretch()
        self._apply_styles()

    # ── Public API ────────────────────────────────────────────────────────────

    def get_selected(self) -> str | None:
        """Return the currently selected label, or None if nothing is selected."""
        return self._selected

    def set_selected(self, label: str) -> None:
        """Select the chip for label; no-op if label is not in options."""
        if label in self._buttons:
            self._selected = label
            self._apply_styles()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _on_click(self, label: str) -> None:
        """Toggle selection: clicking the active chip deselects it."""
        self._selected = None if self._selected == label else label
        self._apply_styles()
        self.selection_changed.emit(self._selected or "")

    def _apply_styles(self) -> None:
        """Restyle all chips based on the current selection."""
        for label, btn in self._buttons.items():
            if label == self._selected:
                color = self._color_map.get(label)
                if color:
                    rgb = _hex_to_rgb(color)
                    btn.setStyleSheet(
                        f"QPushButton {{"
                        f" background: rgba({rgb}, 0.15);"
                        f" border: 1px solid {color};"
                        f" color: {color};"
                        f" {_CHIP_BASE}"
                        f"}}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton {{"
                        f" background: {COLOURS['accent_lo']};"
                        f" border: 1px solid {COLOURS['accent']};"
                        f" color: {COLOURS['accent']};"
                        f" {_CHIP_BASE}"
                        f"}}"
                    )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f" background: transparent;"
                    f" border: 1px solid {COLOURS['border']};"
                    f" color: {COLOURS['muted']};"
                    f" {_CHIP_BASE}"
                    f"}}"
                )
