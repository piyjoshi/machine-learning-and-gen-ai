"""
Interactive CLI for the Self-Correcting SQL Agent.

Provides two entry points:

* :func:`run_agent` — single-shot query execution (importable API).
* :func:`interactive_loop` — REPL with ``cache`` and ``q`` commands.
* ``__main__`` — run via ``python -m src.cli.interactive``.

Example (single query)
----------------------
>>> from src.cli.interactive import run_agent
>>> result = run_agent("Show all users", dialect="MySQL")
>>> print(result["answer"])

Example (interactive)
---------------------
.. code-block:: bash

   $ python -m src.cli.interactive
   🗄️  SQL Agent — Interactive Mode
   📝 Your question: How many orders last month?
   ...
   📝 Your question: q
   🙏 Glad to be of help! See you next time.
"""

from __future__ import annotations

from src.graph.builder import compile_graph


# Module-level compiled app (created once on first use)
_app = None


def _get_app():
    """Lazily compile the agent graph."""
    global _app
    if _app is None:
        _app = compile_graph()
    return _app


def run_agent(
    user_question: str,
    dialect: str = "MySQL",
    max_retries: int = 3,
    thread_id: str = "default",
) -> dict:
    """Execute a single natural-language query through the agent.

    Parameters
    ----------
    user_question : str
        Natural-language question to answer with SQL.
    dialect : str, default ``"MySQL"``
        Target SQL dialect.
    max_retries : int, default ``3``
        Maximum debug-retry cycles.
    thread_id : str, default ``"default"``
        Conversation thread ID for checkpointer memory.

    Returns
    -------
    dict
        Keys:
        - ``answer`` (str) — final natural-language answer.
        - ``sql`` (SQLQuery | None) — last generated SQL.
        - ``execution_result`` (QueryResult | None) — raw result.
        - ``retry_count`` (int) — retries consumed.

    Example
    -------
    >>> result = run_agent("Show top 5 products", dialect="PostgreSQL")
    >>> print(result["answer"])   # doctest: +SKIP
    """
    app = _get_app()
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "user_question": user_question,
        "dialect": dialect,
        "max_retries": max_retries,
        "messages": [],
    }

    accumulated: dict = {}
    for state in app.stream(initial_state, config=config):
        for node_name, node_state in state.items():
            print(f"✓ Completed: {node_name}")
            accumulated.update(node_state)

    return {
        "answer": accumulated.get("final_answer", "Query could not be completed"),
        "sql": accumulated.get("generated_sql"),
        "execution_result": accumulated.get("execution_result"),
        "retry_count": accumulated.get("retry_count", 0),
    }


def interactive_loop(dialect: str = "MySQL") -> None:
    """Start the interactive query REPL.

    Special commands:

    * ``q`` — quit the loop.
    * ``cache`` — print cache statistics.

    Parameters
    ----------
    dialect : str, default ``"MySQL"``
        Default SQL dialect for all queries.
    """
    # Import here so the DB-manager singleton exists by the time we need it
    from src.nodes.executor import _get_db_manager

    db_manager = _get_db_manager()

    print("=" * 60)
    print("🗄️  SQL Agent — Interactive Mode")
    print("Type your question in natural language.")
    print("Type 'cache' to view cache statistics.")
    print("Type 'q' to quit.")
    print("=" * 60)

    query_count = 0

    try:
        while True:
            user_input = input("\n📝 Your question: ").strip()

            if user_input.lower() == "q":
                break

            if user_input.lower() == "cache":
                stats = db_manager.cache.stats()
                print(f"\n📊 Cache Stats: {stats}")
                continue

            if not user_input:
                print("⚠️  Please enter a valid question.")
                continue

            query_count += 1
            print(f"\n{'=' * 60}")
            print(f"QUERY {query_count}: {user_input}")
            print("=" * 60)

            result = run_agent(
                user_input,
                dialect=dialect,
                thread_id=f"interactive-{query_count}",
            )

            print(f"\n✅ Final Answer:\n{result['answer']}")
            print(
                f"\n📄 SQL Used: "
                f"{result['sql'].query if result['sql'] else 'N/A'}"
            )
            print(f"📊 Cache: {db_manager.cache.stats()}")

    except (KeyboardInterrupt, EOFError):
        pass

    print("\n" + "=" * 60)
    print("🙏 Glad to be of help! See you next time.")
    print("=" * 60)


# Allow: python -m src.cli.interactive
if __name__ == "__main__":
    interactive_loop()
