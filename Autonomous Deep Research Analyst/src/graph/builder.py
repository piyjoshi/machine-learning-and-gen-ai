"""LangGraph builder — wires nodes into the research graph."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.models.state import ResearchState
from src.nodes import (
    orchestrator,
    orchestrator_router,
    report_writer,
    research_agent_node,
    synthesiser,
)


def build_research_graph() -> StateGraph:
    """Construct the un-compiled ``StateGraph``.

    Topology::

        START → orchestrator ──[Send()]──→ research_agent (×N parallel)
                                                │
                                                ▼
                                           synthesiser
                                                │
                                                ▼
                                          report_writer
                                                │
                                                ▼
                                               END
    """
    workflow = StateGraph(ResearchState)

    # Register nodes
    workflow.add_node("orchestrator", orchestrator)
    workflow.add_node("research_agent", research_agent_node)
    workflow.add_node("synthesiser", synthesiser)
    workflow.add_node("report_writer", report_writer)

    # Edges
    workflow.add_conditional_edges("orchestrator", orchestrator_router)
    workflow.add_edge("research_agent", "synthesiser")
    workflow.add_edge("synthesiser", "report_writer")
    workflow.add_edge("report_writer", END)

    # Entry point
    workflow.set_entry_point("orchestrator")

    return workflow


def compile_graph():
    """Build and compile the graph, ready for ``.invoke()`` / ``.stream()``."""
    return build_research_graph().compile()
