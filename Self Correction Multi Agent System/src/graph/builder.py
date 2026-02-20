"""
Graph builder — assembles and compiles the LangGraph state machine.

This module wires together all nodes and conditional edges into the
final ``StateGraph[AgentState]``, then compiles it with a
``MemorySaver`` checkpointer for conversation-thread persistence.

Graph topology
--------------
::

    START ──► Planner ──► Sensitive? ──Yes──► Human Approval ──► Approved? ──Yes──► Executor
                                │                                │ No
                                │ No                             └──────────► END
                                ▼
                            Executor ──► Validator ──► Valid? ──Yes──► Answer ──► END
                                                           │ No (retries left)
                                                           ▼
                                                       Debugger ──► Executor (retry)

Example
-------
>>> from src.graph.builder import build_sql_agent_graph, compile_graph
>>> workflow = build_sql_agent_graph()
>>> app = compile_graph(workflow)
>>> type(app).__name__
'CompiledStateGraph'
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.models.state import AgentState
from src.nodes.answer import generate_answer_node
from src.nodes.approval import human_approval
from src.nodes.debugger import debugger_node
from src.nodes.executor import sql_executor_node
from src.nodes.planner import sql_planner
from src.nodes.validator import result_validator
from src.routing.decisions import (
    check_approval_results,
    should_get_approval,
    should_retry_or_complete,
)


def build_sql_agent_graph() -> StateGraph:
    """Construct the LangGraph state machine (uncompiled).

    Returns
    -------
    StateGraph[AgentState]
        The workflow with all nodes and edges registered.

    Example
    -------
    >>> wf = build_sql_agent_graph()
    >>> sorted(wf.nodes)  # doctest: +SKIP
    ['answer', 'debugger', 'executor', 'human_approval', 'planner', 'validator']
    """
    workflow = StateGraph(AgentState)

    # ── Nodes ────────────────────────────────────────────────────────
    workflow.add_node("planner", sql_planner)
    workflow.add_node("human_approval", human_approval)
    workflow.add_node("executor", sql_executor_node)
    workflow.add_node("validator", result_validator)
    workflow.add_node("debugger", debugger_node)
    workflow.add_node("answer", generate_answer_node)

    # ── Entry point ──────────────────────────────────────────────────
    workflow.set_entry_point("planner")

    # ── Edges ────────────────────────────────────────────────────────
    workflow.add_conditional_edges(
        "planner",
        should_get_approval,
        {
            "human_approval": "human_approval",
            "executor": "executor",
        },
    )

    workflow.add_conditional_edges(
        "human_approval",
        check_approval_results,
        {
            "executor": "executor",
            "end": END,
        },
    )

    workflow.add_edge("executor", "validator")

    workflow.add_conditional_edges(
        "validator",
        should_retry_or_complete,
        {
            "debugger": "debugger",
            "answer": "answer",
            "end": END,
        },
    )

    workflow.add_edge("debugger", "executor")  # retry loop
    workflow.add_edge("answer", END)

    return workflow


def compile_graph(
    workflow: StateGraph | None = None,
    *,
    checkpointer=None,
):
    """Compile the workflow into an executable LangGraph app.

    Parameters
    ----------
    workflow : StateGraph or None
        Pre-built workflow.  If ``None``, calls
        :func:`build_sql_agent_graph` internally.
    checkpointer
        LangGraph checkpointer (default: in-memory ``MemorySaver``).

    Returns
    -------
    CompiledStateGraph
        Ready-to-invoke agent application.

    Example
    -------
    >>> app = compile_graph()
    >>> # app.stream(initial_state, config=config)
    """
    if workflow is None:
        workflow = build_sql_agent_graph()
    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)
