"""
Self-Correcting Multi-Agent SQL System.

Top-level convenience imports::

    from src import run_agent, compile_graph, DatabaseManager
"""

from src.cli.interactive import run_agent
from src.db.manager import DatabaseManager
from src.graph.builder import build_sql_agent_graph, compile_graph

__all__ = [
    "run_agent",
    "compile_graph",
    "build_sql_agent_graph",
    "DatabaseManager",
]
