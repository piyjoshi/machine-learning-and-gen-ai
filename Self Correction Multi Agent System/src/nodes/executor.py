"""
SQL Executor node — runs SQL against the database.

This node takes the ``generated_sql`` from the Planner (or the corrected
query from the Debugger) and executes it via
:meth:`DatabaseManager.execute_query`.  The LRU cache is checked first
so repeated queries are served instantly.

Example
-------
>>> from src.nodes.executor import sql_executor_node
>>> state = {"generated_sql": sql_query_obj, "dialect": "MySQL"}
>>> output = sql_executor_node(state)
>>> output["execution_result"].success
True
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.db.manager import DatabaseManager
from src.models.state import AgentState

_db_manager: DatabaseManager | None = None


def _get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def sql_executor_node(state: AgentState) -> dict:
    """Execute the generated SQL query and return results.

    Parameters
    ----------
    state : AgentState
        Must contain ``generated_sql`` and ``dialect``.

    Returns
    -------
    dict
        Keys: ``execution_result`` (:class:`QueryResult`), ``messages``.
    """
    db_manager = _get_db_manager()

    sql = state["generated_sql"]
    dialect = state["dialect"]

    result, from_cache = db_manager.execute_query(dialect, sql.query)
    source = "📦 cache" if from_cache else "🗄️ database"

    return {
        "execution_result": result,
        "messages": [
            HumanMessage(
                content=(
                    f"Execution result ({source}): "
                    f"success={result.success}, rows={result.row_count}"
                )
            )
        ],
    }
