"""
SQL Planner node — converts natural language to SQL.

This is the **entry point** of the agent graph.  It receives the user's
question, introspects the database schema (if not already cached in
state), and asks the LLM to produce a structured :class:`SQLQuery`.

On a **retry** (after the Debugger node), the planner incorporates the
previous error and the debugger's suggested fix into the system prompt
so the LLM can self-correct.

Example
-------
>>> from src.nodes.planner import sql_planner
>>> state = {
...     "user_question": "Show me the top 5 customers by revenue",
...     "dialect": "MySQL",
...     "db_schema": None,
...     "debugger_analysis": None,
... }
>>> output = sql_planner(state)
>>> output["generated_sql"].query  # doctest: +SKIP
'SELECT ...'
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from src.db.manager import DatabaseManager
from src.llm.provider import get_llm
from src.models.schemas import SQLQuery
from src.models.state import AgentState

# Module-level singletons (lazy; override in tests via dependency injection)
_db_manager: DatabaseManager | None = None
_llm = None


def _get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm


def sql_planner(state: AgentState) -> dict:
    """Generate a SQL query from the user's natural-language question.

    Parameters
    ----------
    state : AgentState
        Must contain ``user_question``, ``dialect``.
        Optional: ``db_schema`` (if missing it will be introspected),
        ``debugger_analysis`` (used on retries).

    Returns
    -------
    dict
        Keys: ``generated_sql``, ``db_schema``,
        ``requires_human_approval``, ``messages``.
    """
    db_manager = _get_db_manager()
    llm = _get_llm()

    dialect = state["dialect"]
    schema = state.get("db_schema") or db_manager.get_schema(dialect)
    user_question = state["user_question"]

    # Incorporate debugger feedback on retries
    debug_analysis = state.get("debugger_analysis")

    system_prompt = f"""You are an expert SQL developer. Generate a SQL query for the {dialect} database.

DATABASE SCHEMA:
{schema}

RULES:
1. Use only tables and columns that exist in the schema
2. Use proper {dialect} syntax
3. For aggregations, always include GROUP BY
4. Use appropriate JOINs when accessing multiple tables
5. Mark queries as sensitive if they contain DELETE, UPDATE, DROP, TRUNCATE, or ALTER. Use true or false for boolean fields.
6. Return results in a structured format

{"PREVIOUS ERROR - FIX THIS:" + chr(10) + debug_analysis.root_cause + chr(10) + "Suggested fix:" + debug_analysis.corrected_query if debug_analysis else ""}
"""

    response = llm.with_structured_output(SQLQuery).invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Generate SQL for: {user_question}"),
        ]
    )

    return {
        "generated_sql": response,
        "db_schema": schema,
        "requires_human_approval": response.is_sensitive,
        "messages": [
            HumanMessage(content=f"Generated SQL: {response.query}"),
        ],
    }
