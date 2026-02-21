"""Report sub-package — chart generation and HTML report building."""

from src.report.charts import generate_charts
from src.report.html_report import build_html_report

__all__ = ["build_html_report", "generate_charts"]
