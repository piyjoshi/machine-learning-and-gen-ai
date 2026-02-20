"""
Result Validator node — two-stage validation of query results.

**Stage 1 — Quick checks** (programmatic):
  * Execution success / failure
  * Empty result sets
  * Error messages

**Stage 2 — Semantic validation** (LLM):
  * Do the results actually answer the user's question?
  * Incorrect aggregations or missing columns?
  * Nonsensical data patterns?

Example
-------
>>> from src.nodes.validator import result_validator
>>> output = result_validator(state)
>>> output["validation_result"].is_valid
True
"""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm.provider import get_llm
from src.models.schemas import ValidationResult
from src.models.state import AgentState

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm


def result_validator(state: AgentState) -> dict:
    """Validate query results using quick checks + LLM semantic analysis.

    Parameters
    ----------
    state : AgentState
        Must contain ``execution_result``, ``user_question``,
        ``generated_sql``.

    Returns
    -------
    dict
        Keys: ``validation_result`` (:class:`ValidationResult`),
        ``messages``.
    """
    llm = _get_llm()

    execution_result = state["execution_result"]
    user_question = state["user_question"]
    sql = state["generated_sql"]

    # ------------------------------------------------------------------
    # Stage 1 — Quick programmatic checks
    # ------------------------------------------------------------------
    issues: list[str] = []
    suggestions: list[str] = []

    if not execution_result.success:
        issues.append(
            f"Query execution failed: {execution_result.error_message}"
        )
        suggestions.append("Debug and fix SQL syntax logic")

        return {
            "validation_result": ValidationResult(
                is_valid=False,
                issues=issues,
                suggestions=suggestions,
            ),
            "messages": [HumanMessage(content=f"Validation Failed: {issues}")],
        }

    # ------------------------------------------------------------------
    # Stage 2 — LLM semantic validation
    # ------------------------------------------------------------------
    system_prompt = """You are a SQL result validator. Analyze if the query results properly answer the user's question.

Check for:
1. Empty results when data was expected
2. Incorrect aggregations
3. Missing columns that should be present
4. Data that doesn't make sense for the question

Return your analysis."""

    response = llm.with_structured_output(ValidationResult).invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"""
User Question: {user_question}
SQL Query: {sql.query}
Results (first 5 rows): {json.dumps(
    execution_result.data[:5] if execution_result.data else [],
    default=str,
)}
Row Count: {execution_result.row_count}
"""
            ),
        ]
    )

    return {
        "validation_result": response,
        "messages": [
            HumanMessage(content=f"Validation: valid={response.is_valid}")
        ],
    }
