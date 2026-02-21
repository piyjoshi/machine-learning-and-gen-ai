"""Synthesiser node — merges all sub-agent sections into an executive summary."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from src.llm.provider import llm_invoke
from src.models.state import ResearchState

SYNTHESIS_PROMPT = """\
You are a senior research analyst.  Below are individual research sections
on the topic: **{topic}**.

{sections_text}

──────────────────────────────────────────────
Write a comprehensive **Executive Synthesis** that:
1. Opens with a brief (2-3 sentence) executive overview.
2. Highlights 3-5 cross-cutting themes that span multiple sections.
3. Identifies conflicts or gaps between sections.
4. Provides 3-5 actionable strategic recommendations.
5. Closes with a forward-looking outlook (6-12 months).

Use markdown formatting with ## headings.  Be specific — cite numbers,
companies, or trends from the sections above.
"""


def synthesiser(state: ResearchState) -> dict:
    """Merge parallel agent outputs into a unified synthesis."""
    results = state.get("agent_results", [])

    if not results:
        return {
            "synthesis": "⚠️ No agent results to synthesise.",
            "messages": [AIMessage(content="Synthesiser: no results received.")],
        }

    # Build per-section text block
    blocks: list[str] = []
    for r in results:
        name = r["section_name"] if isinstance(r, dict) else r.section_name
        content = r["content"] if isinstance(r, dict) else r.content
        sources = r["sources"] if isinstance(r, dict) else r.sources

        src_lines: list[str] = []
        for s in sources or []:
            if isinstance(s, dict):
                src_lines.append(f"  - {s.get('title', 'Untitled')} ({s.get('url', '')})")
            else:
                src_lines.append(f"  - {s}")
        src_list = "\n".join(src_lines)
        blocks.append(f"### {name}\n{content}\n\n**Sources:**\n{src_list}")

    sections_text = "\n\n---\n\n".join(blocks)
    prompt = SYNTHESIS_PROMPT.format(topic=state["topic"], sections_text=sections_text)

    print("🧪 Synthesiser: merging all sections into executive summary …")
    synthesis = llm_invoke([HumanMessage(content=prompt)])

    print(f"   ✅ Synthesis complete — {len(synthesis):,} chars")
    return {
        "synthesis": synthesis,
        "messages": [AIMessage(content="Synthesiser: executive summary produced.")],
    }
