"""Minimal tests to verify imports and graph compilation."""

from __future__ import annotations


def test_imports():
    """All public symbols should import cleanly."""
    from src.models import AgentResult, ResearchState, SearchResult, SubAgentInput
    from src.graph import build_research_graph, compile_graph
    from src.nodes import (
        orchestrator,
        orchestrator_router,
        research_agent_node,
        synthesiser,
        report_writer,
    )

    assert callable(orchestrator)
    assert callable(compile_graph)


def test_graph_compiles():
    """The graph should compile without errors."""
    from src.graph import compile_graph

    graph = compile_graph()
    assert graph is not None


def test_search_result_model():
    """SearchResult should accept expected fields."""
    from src.models import SearchResult

    sr = SearchResult(title="Test", url="https://example.com", snippet="Hello")
    assert sr.title == "Test"
    assert sr.score == 0.0


def test_agent_result_model():
    """AgentResult should accept expected fields."""
    from src.models import AgentResult

    ar = AgentResult(section_name="Test", content="Body text")
    assert ar.sources == []
    assert ar.chart_data is None
