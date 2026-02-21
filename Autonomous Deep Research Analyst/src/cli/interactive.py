"""CLI interactive REPL for the Deep Research Analyst."""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv

from src.graph.builder import compile_graph
from src.nodes.orchestrator import DEFAULT_SECTIONS


def _load_env() -> None:
    """Load .env files from standard locations."""
    load_dotenv()
    load_dotenv(".env")


def run_research(topic: str, sections: list[str] | None = None) -> dict:
    """Run the full research pipeline on *topic* and return the final state.

    Parameters
    ----------
    topic : str
        Research subject (e.g. "AI in Healthcare 2025").
    sections : list[str], optional
        Custom research sections. Defaults to
        ``["Market Trends", "Competitor Analysis", "SWOT Analysis"]``.
    """
    _load_env()

    assert os.getenv("GROQ_API_KEY"), "❌ Set GROQ_API_KEY in your .env"
    assert os.getenv("TAVILY_API_KEY"), "❌ Set TAVILY_API_KEY in your .env"

    graph = compile_graph()

    initial_state = {
        "topic": topic,
        "sub_topics": sections or DEFAULT_SECTIONS,
        "agent_results": [],
        "synthesis": "",
        "report_path": "",
        "messages": [],
    }

    print(f"\n{'=' * 60}")
    print(f"  🔬 DEEP RESEARCH ANALYST")
    print(f"  Topic: {topic}")
    print(f"{'=' * 60}\n")

    start = time.time()

    final_state = None
    for event in graph.stream(initial_state, stream_mode="values"):
        final_state = event

    elapsed = time.time() - start

    print(f"\n{'=' * 60}")
    print(f"  ✅ Pipeline complete in {elapsed:.1f}s")
    if final_state and final_state.get("report_path"):
        print(f"  📄 Report: {final_state['report_path']}")
    print(f"{'=' * 60}")

    return final_state or {}


def interactive_loop() -> None:
    """REPL: ask the user for a topic, run research, repeat."""
    _load_env()

    print("\n🔬 Deep Research Analyst — Interactive Mode")
    print("Type a topic to research, or 'quit' to exit.\n")

    while True:
        topic = input("📎 Topic: ").strip()
        if not topic or topic.lower() in {"quit", "exit", "q"}:
            print("👋 Bye!")
            break

        try:
            state = run_research(topic)
            synthesis = state.get("synthesis", "")
            if synthesis:
                print(f"\n{'─' * 60}")
                print("📊 EXECUTIVE SYNTHESIS")
                print(f"{'─' * 60}")
                print(synthesis[:3000])
                if len(synthesis) > 3000:
                    print("… (truncated — see full report)")
        except KeyboardInterrupt:
            print("\n⏹ Interrupted.")
        except Exception as exc:
            print(f"\n❌ Error: {exc}")

        print()
