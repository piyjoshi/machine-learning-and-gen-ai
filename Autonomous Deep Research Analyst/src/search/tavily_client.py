"""Tavily recursive web search with multi-round drill-down."""

from __future__ import annotations

import json
import os
from typing import List

from langchain_core.messages import HumanMessage
from tavily import TavilyClient

from src.config import get_settings
from src.llm.provider import llm_invoke
from src.models.schemas import SearchResult


def _get_client() -> TavilyClient:
    return TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def recursive_search(
    query: str,
    max_depth: int | None = None,
    results_per_round: int | None = None,
) -> List[SearchResult]:
    """Perform multi-round Tavily searches, drilling deeper each round.

    Parameters
    ----------
    query : str
        The initial search query.
    max_depth : int, optional
        Number of recursive drill-down rounds (default from settings).
    results_per_round : int, optional
        Max hits per query per round (default from settings).
    """
    cfg = get_settings()
    max_depth = max_depth or cfg["search"]["max_search_rounds"]
    results_per_round = results_per_round or cfg["search"]["max_results_per_query"]
    search_depth = cfg["search"]["search_depth"]

    tavily = _get_client()
    all_results: dict[str, SearchResult] = {}
    current_queries = [query]

    for depth in range(max_depth):
        next_queries: list[str] = []

        for q in current_queries:
            try:
                raw = tavily.search(
                    query=q,
                    max_results=results_per_round,
                    search_depth=search_depth if depth == 0 else "basic",
                    include_answer=False,
                )
            except Exception as exc:
                print(f"  ⚠️  Tavily error for '{q[:60]}': {exc}")
                continue

            for hit in raw.get("results", []):
                url = hit.get("url", "")
                if url and url not in all_results:
                    all_results[url] = SearchResult(
                        title=hit.get("title", ""),
                        url=url,
                        snippet=hit.get("content", "")[:500],
                        score=hit.get("score", 0.0),
                    )

        # Generate follow-up queries for the next depth round
        if depth < max_depth - 1 and all_results:
            snippets = "\n".join(
                f"- {r.title}: {r.snippet[:150]}"
                for r in list(all_results.values())[-results_per_round:]
            )
            followup_prompt = (
                f"Based on these search results about '{query}':\n{snippets}\n\n"
                f"Generate {results_per_round} specific follow-up search queries "
                f"to find deeper data, statistics, or expert opinions. "
                f"Return ONLY a JSON array of strings."
            )
            try:
                text = llm_invoke([HumanMessage(content=followup_prompt)])
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                next_queries = json.loads(text)
                if not isinstance(next_queries, list):
                    next_queries = []
            except Exception:
                next_queries = []

        current_queries = next_queries[:results_per_round]

    return list(all_results.values())
