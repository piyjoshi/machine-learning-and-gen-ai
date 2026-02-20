"""
Debugger node — root-cause analysis and SQL correction.

When the Executor returns an error or the Validator flags issues, this
node receives the full error context and asks the LLM to:

1. Identify the **root cause** of the failure.
2. Produce a **corrected SQL query**.
3. List the **changes made**.

The corrected query replaces ``generated_sql`` in state, the retry
counter is incremented, and control flows back to the Executor.

Example
-------
>>> from src.nodes.debugger import debugger_node
>>> output = debugger_node(state)
>>> output["debugger_analysis"].root_cause
'Missing GROUP BY clause'
>>> output["retry_count"]
1
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm.provider import get_llm
from src.models.schemas import DebuggerAnalysis, SQLQuery
from src.models.state import AgentState

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm


def debugger_node(state: AgentState) -> dict:
    """Debug a failed query, produce a corrected version, and increment retries.

    Parameters
    ----------
    state : AgentState
        Must contain ``execution_result``, ``validation_result``,
        ``generated_sql``, ``db_schema``, ``dialect``, ``user_question``.

    Returns
    -------
    dict
        Keys: ``debugger_analysis``, ``generated_sql`` (corrected),
        ``retry_count``, ``messages``.
    """
    llm = _get_llm()

    execution_result = state["execution_result"]
    validation_result = state["validation_result"]
    sql = state["generated_sql"]
    schema = state["db_schema"]
    dialect = state["dialect"]
    user_question = state["user_question"]

    # Collect all error information
    error_info: list[str] = []
    if execution_result and not execution_result.success:
        error_info.append(f"Execution Error: {execution_result.error_message}")
    if validation_result and not validation_result.is_valid:
        error_info.extend(validation_result.issues)

    system_prompt = f"""You are an expert SQL debugger. Analyze the failed query and provide a corrected version.

DATABASE DIALECT: {dialect}

DATABASE SCHEMA:
{schema}

ORIGINAL QUERY:
{sql.query}

ERRORS:
{chr(10).join(error_info)}

Analyze the root cause and provide a corrected query that will work."""

    response = llm.with_structured_output(DebuggerAnalysis).invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Fix this query to answer: {user_question}"),
        ]
    )

    # Replace the generated SQL with the corrected version
    corrected_sql = SQLQuery(
        query=response.corrected_query,
        explanation=f"Corrected: {response.root_cause}",
        is_sensitive=sql.is_sensitive,
        dialect=dialect,
    )

    return {
        "debugger_analysis": response,
        "generated_sql": corrected_sql,
        "retry_count": state.get("retry_count", 0) + 1,
        "messages": [HumanMessage(content=f"Debug: {response.root_cause}")],
    }
