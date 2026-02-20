"""
Human approval gate for sensitive SQL queries.

This node pauses the pipeline and asks the user to approve any query
flagged as *sensitive* (DELETE, UPDATE, DROP, TRUNCATE, ALTER).

In a **production** environment you would replace the ``input()`` call
with an async callback, a Slack webhook, or an API endpoint.

Example
-------
>>> # In an interactive session:
>>> from src.nodes.approval import human_approval
>>> state = {
...     "generated_sql": SQLQuery(
...         query="DROP TABLE logs",
...         explanation="Remove the logs table",
...         is_sensitive=True,
...         dialect="MySQL",
...     ),
... }
>>> output = human_approval(state)   # prompts for input
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.models.state import AgentState


def human_approval(state: AgentState) -> dict:
    """Prompt the user to approve or reject a sensitive query.

    Parameters
    ----------
    state : AgentState
        Must contain ``generated_sql`` (:class:`SQLQuery`).

    Returns
    -------
    dict
        Keys: ``human_approved`` (bool), ``messages``.

    Notes
    -----
    * In notebook / CLI mode this blocks on ``input()``.
    * Replace with an async callback for web / API deployments.
    """
    sql_query = state["generated_sql"]

    print("\n" + "=" * 60)
    print("⚠️  SENSITIVE QUERY REQUIRES APPROVAL")
    print("=" * 60)
    print(f"\nQuery: {sql_query.query}")
    print(f"\nExplanation: {sql_query.explanation}")
    print("\nThis query will modify data. Do you approve?")

    approval = (
        input("Type 'yes' to approve, anything else to reject: ").strip().lower()
    )

    return {
        "human_approved": approval == "yes",
        "messages": [HumanMessage(content=f"Human approval: {approval == 'yes'}")],
    }
