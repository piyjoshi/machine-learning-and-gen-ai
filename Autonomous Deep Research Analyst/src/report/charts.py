"""Matplotlib chart generation from agent results."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt


def generate_charts(results: list[dict], output_dir: Path) -> dict[str, Path]:
    """Create Matplotlib charts from ``chart_data`` in agent results.

    Returns a mapping ``{section_key: png_path}``.
    """
    chart_paths: dict[str, Path] = {}

    for r in results:
        chart_data = r.get("chart_data")
        if not chart_data:
            continue

        section = r.get("section_name", "chart")
        safe_name = section.lower().replace(" ", "_")

        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])
        chart_type = chart_data.get("type", "bar")
        chart_title = chart_data.get("title", section)

        if not labels or not values:
            continue

        fig, ax = plt.subplots(figsize=(8, 5))
        if chart_type == "pie":
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
        elif chart_type == "horizontal_bar":
            ax.barh(labels, values, color="steelblue")
            ax.set_xlabel("Value")
        else:
            ax.bar(labels, values, color="steelblue")
            ax.set_ylabel("Value")
            plt.xticks(rotation=30, ha="right")

        ax.set_title(chart_title, fontsize=13, fontweight="bold")
        fig.tight_layout()

        path = output_dir / f"{safe_name}_chart.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        chart_paths[safe_name] = path
        print(f"   📊 Chart saved → {path}")

    return chart_paths
