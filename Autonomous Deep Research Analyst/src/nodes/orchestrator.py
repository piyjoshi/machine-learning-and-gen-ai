"""Orchestrator node — plans research sections and dispatches sub-agents."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.types import Send

from src.models.state import ResearchState

# Default research sections produced for every topic
DEFAULT_SECTIONS = ["Market Trends", "Competitor Analysis", "SWOT Analysis"]


def orchestrator(state: ResearchState) -> dict:
    """Plan research sections and update state.

    This is the graph **node** — it returns a normal state-update dict.
    Parallel dispatch via ``Send()`` is handled by :func:`orchestrator_router`.
    """
    topic = state["topic"]
    sections = state.get("sub_topics") or DEFAULT_SECTIONS

    print(f"\n🎯 Orchestrator: researching '{topic}'")
    print(f"   Sections: {sections}")
    print(f"   → Dispatching {len(sections)} sub-agents in parallel …\n")

    return {
        "sub_topics": sections,
        "messages": [HumanMessage(content=f"Orchestrator: planning {len(sections)} sections")],
    }


def orchestrator_router(state: ResearchState) -> list[Send]:
    """Routing function for conditional edges — returns ``Send()`` commands.

    LangGraph executes these concurrently on the ``research_agent`` node.
    """
    topic = state["topic"]
    sections = state.get("sub_topics") or DEFAULT_SECTIONS

    return [
        Send(
            "research_agent",
            {
                "topic": topic,
                "section_name": section,
                "search_depth": 2,
            },
        )
        for section in sections
    ]
