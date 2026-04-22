"""Analytics tab for the Job Application Tracker."""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jat.analytics.charts import (
    category_bar_chart,
    status_bar_chart,
    timeline_chart,
    work_mode_pie_chart,
)
from jat.analytics.queries import (
    applications_by_category,
    applications_by_status,
    applications_by_work_mode,
    applications_over_time,
    summary_stats,
)
from jat.database.connection import get_connection

_CHARTS = [
    ("Applications by Status", applications_by_status, status_bar_chart),
    ("Applications Over Time", applications_over_time, timeline_chart),
    ("Applications by Category", applications_by_category, category_bar_chart),
    ("Applications by Work Mode", applications_by_work_mode, work_mode_pie_chart),
]


class AnalyticsTab(QWidget):
    """Summary stats and chart explorer for all application data."""

    def __init__(self, parent=None) -> None:
        """Build the layout and load initial data."""
        super().__init__(parent)

        root = QVBoxLayout(self)

        # ── Top row: summary stats + Refresh ────────────────────────────────
        top_row = QHBoxLayout()

        self._lbl_total = self._make_stat_label("Total: —")
        self._lbl_active = self._make_stat_label("Active: —")
        self._lbl_response = self._make_stat_label("Response rate: —")
        self._lbl_priority = self._make_stat_label("Avg priority: —")

        for lbl in (
            self._lbl_total,
            self._lbl_active,
            self._lbl_response,
            self._lbl_priority,
        ):
            top_row.addWidget(lbl)

        top_row.addStretch()

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.clicked.connect(self._load_data)
        top_row.addWidget(self._btn_refresh)

        root.addLayout(top_row)

        # ── Chart selector ───────────────────────────────────────────────────
        self._combo = QComboBox()
        for name, _, _ in _CHARTS:
            self._combo.addItem(name)
        self._combo.currentIndexChanged.connect(self._on_chart_changed)
        root.addWidget(self._combo)

        # ── Canvas area ──────────────────────────────────────────────────────
        self._canvas: FigureCanvasQTAgg | None = None
        self._canvas_container = QVBoxLayout()
        canvas_wrapper = QWidget()
        canvas_wrapper.setLayout(self._canvas_container)
        root.addWidget(canvas_wrapper, stretch=1)

        self._load_data()

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_stat_label(text: str) -> QLabel:
        """Return a framed, padded QLabel suitable for a summary stat box."""
        lbl = QLabel(text)
        lbl.setFrameShape(QFrame.Shape.Box)
        lbl.setMargin(8)
        return lbl

    def _load_data(self) -> None:
        """Re-run summary stats and redraw the current chart."""
        self._refresh_stats()
        self._render_chart(self._combo.currentIndex())

    def _refresh_stats(self) -> None:
        """Fetch and display the four summary stat values."""
        with get_connection() as conn:
            stats = summary_stats(conn)
        self._lbl_total.setText(f"Total: {stats['total_applications']}")
        self._lbl_active.setText(f"Active: {stats['active_applications']}")
        rate = stats["response_rate"]
        self._lbl_response.setText(f"Response rate: {rate:.0%}")
        self._lbl_priority.setText(f"Avg priority: {stats['avg_priority']}")

    def _render_chart(self, index: int) -> None:
        """Fetch data and render the chart for the given _CHARTS index."""
        _, query_fn, chart_fn = _CHARTS[index]
        with get_connection() as conn:
            data = query_fn(conn)
        fig = chart_fn(data)

        if self._canvas is not None:
            old_fig = self._canvas.figure
            self._canvas_container.removeWidget(self._canvas)
            self._canvas.deleteLater()
            plt.close(old_fig)

        self._canvas = FigureCanvasQTAgg(fig)
        self._canvas_container.addWidget(self._canvas)

    # ── Slot handlers ────────────────────────────────────────────────────────

    def _on_chart_changed(self, index: int) -> None:
        """Render the newly selected chart."""
        self._render_chart(index)
