"""
Routing / decision functions for the agent graph edges.

Each function inspects ``AgentState`` and returns a **string label**
that maps to the next node in the LangGraph conditional edges.

Functions
---------
``should_get_approval``
    Planner → Human Approval *or* Executor.
``check_approval_results``
    Human Approval → Executor *or* END.
``should_retry_or_complete``
    Validator → Debugger, Answer Generator, *or* END.

Example
-------
>>> from src.routing.decisions import should_get_approval
>>> state = {"requires_human_approval": True}
>>> should_get_approval(state)
'human_approval'
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END

from src.models.state import AgentState


def should_get_approval(
    state: AgentState,
) -> Literal["human_approval", "executor"]:
    """Route based on whether the query needs human approval.

    Parameters
    ----------
    state : AgentState
        Must contain ``requires_human_approval``.

    Returns
    -------
    ``"human_approval"`` if the query is sensitive, else ``"executor"``.

    Example
    -------
    >>> should_get_approval({"requires_human_approval": False})
    'executor'
    """
    if state.get("requires_human_approval", False):
        return "human_approval"
    return "executor"


def check_approval_results(
    state: AgentState,
) -> Literal["executor", "end"]:
    """Route to Executor if approved, otherwise END.

    Parameters
    ----------
    state : AgentState
        Must contain ``human_approved``.

    Returns
    -------
    ``"executor"`` if approved, :data:`langgraph.graph.END` otherwise.

    Example
    -------
    >>> check_approval_results({"human_approved": True})
    'executor'
    """
    if state.get("human_approved"):
        return "executor"
    return END


def should_retry_or_complete(
    state: AgentState,
) -> Literal["debugger", "answer", "end"]:
    """Determine the next step after validation.

    Decision logic:

    * **Execution failed or validation invalid** and retries remain →
      ``"debugger"``
    * **Validation passed** → ``"answer"``
    * **Retries exhausted** → ``END``

    Parameters
    ----------
    state : AgentState
        Must contain ``validation_result``, ``execution_result``,
        ``retry_count``, ``max_retries``.

    Returns
    -------
    ``"debugger"``, ``"answer"``, or :data:`langgraph.graph.END`.

    Example
    -------
    >>> from src.models.schemas import QueryResult, ValidationResult
    >>> state = {
    ...     "execution_result": QueryResult(success=True, row_count=5),
    ...     "validation_result": ValidationResult(is_valid=True),
    ...     "retry_count": 0,
    ...     "max_retries": 3,
    ... }
    >>> should_retry_or_complete(state)
    'answer'
    """
    validation = state.get("validation_result")
    execution = state.get("execution_result")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    # Execution or validation failure
    if (execution and not execution.success) or (
        validation and not validation.is_valid
    ):
        if retry_count < max_retries:
            return "debugger"
        return "end"  # max retries exhausted

    return "answer"
