"""Pydantic schemas for the Deep Research Analyst pipeline."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single search hit from Tavily."""

    title: str
    url: str
    snippet: str
    score: float = 0.0


class AgentResult(BaseModel):
    """Output produced by one research sub-agent."""

    section_name: str = Field(description="e.g. 'Market Trends'")
    content: str = Field(description="Markdown analysis text")
    sources: List[SearchResult] = Field(default_factory=list)
    chart_data: Optional[dict] = Field(
        default=None,
        description="Optional {labels: [...], values: [...]} for charting",
    )
