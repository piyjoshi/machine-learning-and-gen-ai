"""
Answer Generator node — converts SQL results to natural language.

This is the **final processing node** before ``END``.  It receives the
validated query results and asks the LLM to produce a clear,
insight-rich natural-language answer.

Example
-------
>>> from src.nodes.answer import generate_answer_node
>>> output = generate_answer_node(state)
>>> print(output["final_answer"])
The top 5 customers by revenue are …
"""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm.provider import get_llm
from src.models.state import AgentState

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm


def generate_answer_node(state: AgentState) -> dict:
    """Generate a natural-language answer from validated SQL results.

    Parameters
    ----------
    state : AgentState
        Must contain ``execution_result``, ``user_question``,
        ``generated_sql``.

    Returns
    -------
    dict
        Keys: ``final_answer`` (str), ``messages``.
    """
    llm = _get_llm()

    execution_result = state["execution_result"]
    user_question = state["user_question"]
    sql = state["generated_sql"]

    system_prompt = (
        "You are a data analyst. Convert the SQL results into a clear, "
        "natural language answer.\n"
        "Include key insights and numbers from the data."
    )

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"""
Question: {user_question}
SQL Used: {sql.query}
Results: {json.dumps(
    execution_result.data[:20] if execution_result.data else [],
    default=str,
)}
Total Rows: {execution_result.row_count}

Provide a comprehensive answer."""
            ),
        ]
    )

    return {
        "final_answer": response.content,
        "messages": [HumanMessage(content=response.content)],
    }
