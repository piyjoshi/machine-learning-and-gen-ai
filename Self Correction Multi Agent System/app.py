"""
Streamlit UI for the Self-Correcting Multi-Agent SQL System.

Launch with:
    streamlit run app.py
"""

from __future__ import annotations

import os
import time
import uuid

import streamlit as st
from dotenv import load_dotenv

# ── Load env before any src imports ──────────────────────────────────
load_dotenv()

from src.db.manager import DatabaseManager, _ENV_VAR_MAP  # noqa: E402
from src.graph.builder import compile_graph  # noqa: E402
from src.models.schemas import SQLQuery  # noqa: E402

# ─────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SQL Agent",
    page_icon="🗄️",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────
# Session-state singletons
# ─────────────────────────────────────────────────────────────────────
if "app" not in st.session_state:
    st.session_state.app = compile_graph()

if "db_manager" not in st.session_state:
    st.session_state.db_manager = DatabaseManager()

if "history" not in st.session_state:
    st.session_state.history = []  # list of past query dicts


def _available_databases() -> dict[str, str]:
    """Return {dialect: connection_string} for every DB configured in .env."""
    available: dict[str, str] = {}
    for dialect, env_var in _ENV_VAR_MAP.items():
        conn_str = os.getenv(env_var, "").strip()
        if conn_str:
            available[dialect] = conn_str
    # Always offer SQLite (zero-config)
    if "SQLite" not in available:
        available["SQLite"] = os.getenv(
            "SQLITE_CONNECTION_STRING", "sqlite:///./database.db"
        )
    return available


def _run_workflow(question: str, dialect: str) -> dict:
    """Execute the agent graph and capture per-node progress."""
    app = st.session_state.app
    db_manager: DatabaseManager = st.session_state.db_manager

    thread_id = f"st-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "user_question": question,
        "dialect": dialect,
        "max_retries": 3,
        "messages": [],
    }

    steps: list[dict] = []
    accumulated: dict = {}
    start = time.time()

    for state_chunk in app.stream(initial_state, config=config):
        for node_name, node_state in state_chunk.items():
            elapsed = round(time.time() - start, 2)
            steps.append({"node": node_name, "elapsed_s": elapsed})
            accumulated.update(node_state)

    sql_obj: SQLQuery | None = accumulated.get("generated_sql")
    exec_result = accumulated.get("execution_result")

    return {
        "answer": accumulated.get("final_answer", "Query could not be completed."),
        "sql": sql_obj.query if sql_obj else None,
        "explanation": sql_obj.explanation if sql_obj else None,
        "execution_result": exec_result,
        "rows": exec_result.data if exec_result and exec_result.data else [],
        "row_count": exec_result.row_count if exec_result else 0,
        "success": exec_result.success if exec_result else False,
        "retry_count": accumulated.get("retry_count", 0),
        "steps": steps,
        "cache_stats": db_manager.cache.stats(),
        "elapsed_s": round(time.time() - start, 2),
    }


# ─────────────────────────────────────────────────────────────────────
# Sidebar — Database selector & cache stats
# ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    available_dbs = _available_databases()

    if not available_dbs:
        st.error(
            "No database connections found. "
            "Add connection strings to your `.env` file."
        )
        st.stop()

    selected_dialect = st.selectbox(
        "🗄️ Select Database",
        options=list(available_dbs.keys()),
        help="Databases are detected from environment variables in `.env`.",
    )

    # Show connection string (masked)
    conn_str = available_dbs[selected_dialect]
    masked = conn_str[:20] + "•••" if len(conn_str) > 20 else conn_str
    st.caption(f"Connection: `{masked}`")

    st.divider()

    # Cache statistics
    st.subheader("📊 Cache Statistics")
    cache_stats = st.session_state.db_manager.cache.stats()
    col1, col2 = st.columns(2)
    col1.metric("Entries", cache_stats["entries"])
    col2.metric("Hit Rate", cache_stats["hit_rate"])
    col1.metric("Hits", cache_stats["hits"])
    col2.metric("Misses", cache_stats["misses"])
    st.caption(
        f"Size: {cache_stats['size_mb']} / {cache_stats['max_size_mb']} MB"
    )

    if st.button("🗑️ Clear Cache"):
        st.session_state.db_manager.cache.clear()
        st.rerun()

    st.divider()
    st.subheader("📜 Query History")
    for i, h in enumerate(reversed(st.session_state.history), 1):
        with st.expander(f"{i}. {h['question'][:50]}…"):
            st.code(h.get("sql", "N/A"), language="sql")
            st.caption(f"Rows: {h['row_count']} · Time: {h['elapsed_s']}s")

# ─────────────────────────────────────────────────────────────────────
# Main area
# ─────────────────────────────────────────────────────────────────────
st.title("🗄️ Self-Correcting SQL Agent")
st.caption(
    "Ask a question in plain English — the agent generates SQL, "
    "executes it, validates the results, and auto-corrects on failure."
)

# Query input
with st.form("query_form", clear_on_submit=False):
    user_question = st.text_area(
        "📝 Ask a question about your data",
        placeholder="e.g., Show me the top 10 customers by total revenue",
        height=100,
    )
    submitted = st.form_submit_button(
        "🚀 Execute", type="primary", use_container_width=True
    )

# ─────────────────────────────────────────────────────────────────────
# Run workflow on submit
# ─────────────────────────────────────────────────────────────────────
if submitted and user_question.strip():
    with st.status("Running agent workflow…", expanded=True) as status:
        st.write(f"**Database:** {selected_dialect}")
        st.write(f"**Question:** {user_question}")

        result = _run_workflow(user_question.strip(), selected_dialect)

        # Show step-by-step progress
        for step in result["steps"]:
            st.write(f"✅ **{step['node']}** — {step['elapsed_s']}s")

        if result["success"]:
            status.update(
                label=f"✅ Completed in {result['elapsed_s']}s",
                state="complete",
            )
        else:
            status.update(
                label=f"⚠️ Completed with issues ({result['elapsed_s']}s)",
                state="error",
            )

    # ── Answer ───────────────────────────────────────────────────────
    st.subheader("💬 Answer")
    st.info(result["answer"])

    # ── SQL Query ────────────────────────────────────────────────────
    if result["sql"]:
        with st.expander("📄 Generated SQL", expanded=True):
            st.code(result["sql"], language="sql")
            if result["explanation"]:
                st.caption(f"💡 {result['explanation']}")

    # ── Results table ────────────────────────────────────────────────
    if result["rows"]:
        st.subheader("📊 Results")
        st.dataframe(
            result["rows"],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Showing {len(result['rows'])} of {result['row_count']} rows")
    elif result["success"]:
        st.success(f"Query executed successfully. Rows affected: {result['row_count']}")

    # ── Metadata ─────────────────────────────────────────────────────
    meta_cols = st.columns(3)
    meta_cols[0].metric("⏱️ Time", f"{result['elapsed_s']}s")
    meta_cols[1].metric("🔄 Retries", result["retry_count"])
    meta_cols[2].metric("📦 Cache Hit Rate", result["cache_stats"]["hit_rate"])

    # Save to history
    st.session_state.history.append(
        {
            "question": user_question.strip(),
            "sql": result["sql"],
            "row_count": result["row_count"],
            "elapsed_s": result["elapsed_s"],
        }
    )

elif submitted:
    st.warning("Please enter a question before submitting.")
