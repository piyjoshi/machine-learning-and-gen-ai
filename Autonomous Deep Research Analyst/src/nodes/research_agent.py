"""Research sub-agent node — search → synthesise → return AgentResult."""

from __future__ import annotations

import json
import textwrap
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm.provider import llm_invoke
from src.models.schemas import AgentResult
from src.models.state import SubAgentInput
from src.search.tavily_client import recursive_search

# ── Per-section system prompts ──────────────────────────────────────

SECTION_PROMPTS: dict[str, str] = {
    "Market Trends": textwrap.dedent("""\
        You are an expert market research analyst.
        Given the search results below, write a detailed **Market Trends** section:
        - Identify 3-5 key trends with supporting data/statistics.
        - Include market size, growth rates, and projections where available.
        - Cite sources inline as [Source Title](url).
        - At the end, output a JSON block fenced with ```chart_data``` containing
          {{"labels": ["Trend1", ...], "values": [number, ...]}} for a bar chart
          of the top trends by relevance score (1-10).
        Write in professional Markdown.
    """),
    "Competitor Analysis": textwrap.dedent("""\
        You are an expert competitive intelligence analyst.
        Given the search results below, write a detailed **Competitor Analysis** section:
        - Identify the top 5 competitors / key players.
        - Compare their strengths, market share, key products, and strategies.
        - Use a Markdown table for the comparison matrix.
        - Cite sources inline as [Source Title](url).
        - At the end, output a JSON block fenced with ```chart_data``` containing
          {{"labels": ["Company1", ...], "values": [market_share_pct, ...]}}
          for a pie/bar chart.
        Write in professional Markdown.
    """),
    "SWOT Analysis": textwrap.dedent("""\
        You are a strategic business analyst.
        Given the search results below, write a detailed **SWOT Analysis** section:
        - **Strengths**: internal advantages.
        - **Weaknesses**: internal limitations.
        - **Opportunities**: external factors to exploit.
        - **Threats**: external risks.
        - Provide 3-5 bullet points per quadrant with evidence from sources.
        - Cite sources inline as [Source Title](url).
        - At the end, output a JSON block fenced with ```chart_data``` containing
          {{"labels": ["Strengths", "Weaknesses", "Opportunities", "Threats"],
            "values": [count_of_items, count, count, count]}}
        Write in professional Markdown.
    """),
}


def _extract_chart_data(text: str) -> tuple[str, Optional[dict]]:
    """Extract ``chart_data`` JSON block from LLM output."""
    chart_data = None
    if "```chart_data" in text:
        parts = text.split("```chart_data")
        clean = parts[0]
        try:
            json_block = parts[1].split("```")[0].strip()
            chart_data = json.loads(json_block)
        except (IndexError, json.JSONDecodeError):
            pass
        return clean.strip(), chart_data
    return text.strip(), None


def research_agent_node(state: SubAgentInput) -> dict:
    """Generic sub-agent: search → synthesise → return AgentResult."""
    topic = state["topic"]
    section = state["section_name"]
    depth = state.get("search_depth", 2)

    print(f"  🔍 [{section}] Searching for: {topic} (depth={depth})")

    # 1. Recursive search
    results = recursive_search(
        query=f"{topic} {section.lower()}",
        max_depth=depth,
        results_per_round=5,
    )
    print(f"  📄 [{section}] Got {len(results)} search results")

    # 2. Build context from search hits
    search_context = "\n\n".join(
        f"### {r.title}\n**URL:** {r.url}\n{r.snippet}" for r in results
    )

    # 3. LLM synthesis (with retry + fallback)
    system_prompt = SECTION_PROMPTS.get(section, f"Write a detailed {section} section.")
    user_msg = (
        f"Research topic: **{topic}**\n\n"
        f"Here are the search results:\n\n{search_context}\n\n"
        f"Now write the {section} section."
    )

    raw_content = llm_invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ]
    )

    content, chart_data = _extract_chart_data(raw_content)

    agent_result = AgentResult(
        section_name=section,
        content=content,
        sources=results[:10],
        chart_data=chart_data,
    )

    print(f"  ✅ [{section}] Analysis complete ({len(content)} chars)")

    return {
        "agent_results": [agent_result.model_dump()],
        "messages": [HumanMessage(content=f"[{section}] completed")],
    }
