"""
Deep Research Analyst — Autonomous multi-agent research system.

Quick usage::

    from src import run_research

    state = run_research("Artificial Intelligence in Healthcare 2025")
    print(state["report_path"])
"""

from src.cli.interactive import interactive_loop, run_research
from src.graph.builder import build_research_graph, compile_graph

__all__ = [
    "build_research_graph",
    "compile_graph",
    "interactive_loop",
    "run_research",
]
