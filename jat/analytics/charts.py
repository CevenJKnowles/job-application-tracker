"""Matplotlib figure builders for the Job Application Tracker analytics tab."""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator


def status_bar_chart(data: list[dict], figsize: tuple = (7, 4)) -> Figure:
    """Return a horizontal bar chart of applications by status."""
    labels = [row["label"] for row in data]
    counts = [row["count"] for row in data]
    cmap = plt.get_cmap("tab10")
    colors = [cmap(i % 10) for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=figsize)
    ax.barh(labels, counts, color=colors)
    ax.set_title("Applications by Status")
    ax.set_xlabel("Count")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlim(left=0)
    fig.tight_layout()
    return fig


def timeline_chart(data: list[dict], figsize: tuple = (8, 4)) -> Figure:
    """Return a line chart of applications over time."""
    periods = [row["period"] for row in data]
    counts = [row["count"] for row in data]

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(periods, counts, marker="o")
    ax.set_title("Applications Over Time")
    ax.set_xlabel("Period")
    ax.set_ylabel("Count")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    return fig


def category_bar_chart(data: list[dict], figsize: tuple = (7, 4)) -> Figure:
    """Return a horizontal bar chart of applications by category."""
    labels = [row["label"] for row in data]
    counts = [row["count"] for row in data]
    cmap = plt.get_cmap("tab10")
    colors = [cmap(i % 10) for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=figsize)
    ax.barh(labels, counts, color=colors)
    ax.set_title("Applications by Category")
    ax.set_xlabel("Count")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlim(left=0)
    fig.tight_layout()
    return fig


def work_mode_pie_chart(data: list[dict], figsize: tuple = (5, 5)) -> Figure:
    """Return a pie chart of applications by work mode."""
    labels = [row["label"] for row in data]
    counts = [row["count"] for row in data]

    fig, ax = plt.subplots(figsize=figsize)
    ax.pie(counts, labels=labels, autopct="%1.0f%%")
    ax.set_title("Applications by Work Mode")
    fig.tight_layout()
    return fig
