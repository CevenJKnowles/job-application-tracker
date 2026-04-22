"""Export format and directory dialog for the Job Application Tracker."""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt


class ExportDialog(QDialog):
    """Dialog for selecting export formats and output directory."""

    def __init__(
        self,
        report_type: str,
        base_stem: str,
        parent=None,
    ) -> None:
        """Initialise the dialog for report_type with filename stem base_stem."""
        super().__init__(parent)
        self._base_stem = base_stem
        self._selected_formats: list[str] = []
        self._export_directory: str = ""

        titles = {
            "afa_table": "Export — Bewerbungsliste",
            "application_sheet": "Export — Bewerbungsblatt",
            "analytics_summary": "Export — Analytik-Bericht",
        }
        self.setWindowTitle(titles.get(report_type, "Export"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_format_group())
        layout.addWidget(self._build_directory_group())
        layout.addWidget(self._build_button_box())

        self._update_ok_state()

    # ------------------------------------------------------------------
    # Group builders
    # ------------------------------------------------------------------

    def _build_format_group(self) -> QGroupBox:
        """Build the Formate group box with format checkboxes."""
        from PyQt6.QtWidgets import QCheckBox

        group = QGroupBox("Formate")
        vbox = QVBoxLayout(group)

        self._cb_tex = QCheckBox("TeX (.tex)")
        self._cb_pdf = QCheckBox("PDF (.pdf)")
        self._cb_docx = QCheckBox("Word (.docx)")
        self._cb_odt = QCheckBox("OpenDocument (.odt)")

        self._format_checkboxes = [
            (self._cb_tex, "tex"),
            (self._cb_pdf, "pdf"),
            (self._cb_docx, "docx"),
            (self._cb_odt, "odt"),
        ]

        for cb, _ in self._format_checkboxes:
            vbox.addWidget(cb)
            cb.stateChanged.connect(self._on_format_changed)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        vbox.addWidget(divider)

        self._cb_all = QCheckBox("Alle Formate")
        self._cb_all.stateChanged.connect(self._on_all_changed)
        vbox.addWidget(self._cb_all)

        return group

    def _build_directory_group(self) -> QGroupBox:
        """Build the Speicherort group box with path field and browse button."""
        group = QGroupBox("Speicherort")
        hbox = QHBoxLayout(group)

        self._path_field = QLineEdit()
        self._path_field.setReadOnly(True)
        self._path_field.setPlaceholderText("Verzeichnis wählen…")
        self._path_field.textChanged.connect(self._update_ok_state)
        hbox.addWidget(self._path_field)

        browse_btn = QPushButton("Durchsuchen…")
        browse_btn.clicked.connect(self._on_browse)
        hbox.addWidget(browse_btn)

        return group

    def _build_button_box(self) -> QDialogButtonBox:
        """Build the OK / Cancel button box."""
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_accepted)
        self._button_box.rejected.connect(self.reject)
        return self._button_box

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_format_changed(self) -> None:
        """Uncheck 'Alle Formate' if any individual checkbox is unchecked."""
        all_checked = all(cb.isChecked() for cb, _ in self._format_checkboxes)
        self._cb_all.blockSignals(True)
        self._cb_all.setChecked(all_checked)
        self._cb_all.blockSignals(False)
        self._update_ok_state()

    def _on_all_changed(self, state: int) -> None:
        """Check or uncheck all format boxes when 'Alle Formate' changes."""
        checked = state == Qt.CheckState.Checked.value
        for cb, _ in self._format_checkboxes:
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._update_ok_state()

    def _on_browse(self) -> None:
        """Open a directory picker and write the result into the path field."""
        directory = QFileDialog.getExistingDirectory(
            self, "Exportverzeichnis wählen", self._path_field.text() or ""
        )
        if directory:
            self._path_field.setText(directory)

    def _update_ok_state(self) -> None:
        """Enable OK only when at least one format is checked and path is set."""
        any_format = any(cb.isChecked() for cb, _ in self._format_checkboxes)
        has_path = bool(self._path_field.text().strip())
        ok_btn = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setEnabled(any_format and has_path)

    def _on_accepted(self) -> None:
        """Collect selected formats and directory before accepting."""
        self._selected_formats = [
            ext for cb, ext in self._format_checkboxes if cb.isChecked()
        ]
        self._export_directory = self._path_field.text().strip()
        self.accept()

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def selected_formats(self) -> list[str]:
        """Subset of ['tex', 'pdf', 'docx', 'odt'] matching checked boxes."""
        return self._selected_formats

    @property
    def export_directory(self) -> str:
        """The chosen directory path."""
        return self._export_directory
