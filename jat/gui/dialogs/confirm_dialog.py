"""Generic yes/no confirmation dialog."""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class ConfirmDialog(QDialog):
    """Modal dialog that asks the user to confirm a destructive action."""

    def __init__(self, message: str, parent=None) -> None:
        """Build the dialog with message and Yes/No buttons."""
        super().__init__(parent)
        self.setWindowTitle("Confirm")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(message))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
