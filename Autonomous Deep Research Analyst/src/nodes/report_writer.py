"""Report writer node — generates a self-contained HTML report."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from langchain_core.messages import AIMessage

from src.config import get_settings
from src.models.state import ResearchState
from src.report.charts import generate_charts
from src.report.html_report import build_html_report


def report_writer(state: ResearchState) -> dict:
    """Generate an HTML report with embedded charts."""
    cfg = get_settings()
    topic = state["topic"]
    results = state.get("agent_results", [])
    synthesis = state.get("synthesis", "No synthesis available.")

    output_dir = Path(cfg["report"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = topic.lower().replace(" ", "_")[:40]
    output_path = output_dir / f"{safe_topic}_{timestamp}.html"

    print("📝 Report Writer: generating HTML report …")

    chart_paths = generate_charts(results, output_dir)
    build_html_report(topic, results, synthesis, chart_paths, output_path)

    print(f"   ✅ Report saved → {output_path}")
    return {
        "report_path": str(output_path),
        "messages": [AIMessage(content=f"Report saved to {output_path}")],
    }
