"""Graph state definitions (TypedDict) for the LangGraph pipeline."""

from __future__ import annotations

import operator
from typing import Annotated, List, Optional, TypedDict


class SubAgentInput(TypedDict):
    """Payload sent to each parallel sub-agent via ``Send()``."""

    topic: str
    section_name: str
    search_depth: int  # how many recursive search rounds


class ResearchState(TypedDict):
    """Top-level shared state flowing through the research graph."""

    topic: str  # user's research subject
    sub_topics: List[str]  # planned sub-sections
    agent_results: Annotated[list, operator.add]  # accumulates AgentResult dicts
    synthesis: Optional[str]  # merged final analysis
    report_path: Optional[str]  # path to generated report
    messages: Annotated[list, operator.add]  # audit trail
