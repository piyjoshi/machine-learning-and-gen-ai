"""
LangGraph agent state definition.

This module defines the shared ``AgentState`` TypedDict that flows between
every node in the self-correcting SQL agent graph.

Each key is documented with its purpose and which node(s) write to it.

Example
-------
>>> from src.models.state import AgentState
>>> state: AgentState = {
...     "user_question": "Show all active users",
...     "dialect": "MySQL",
...     "db_schema": "",
...     "generated_sql": None,
...     "execution_result": None,
...     "validation_result": None,
...     "debugger_analysis": None,
...     "requires_human_approval": False,
...     "human_approved": False,
...     "retry_count": 0,
...     "max_retries": 3,
...     "final_answer": None,
...     "messages": [],
... }
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.models.schemas import (
    DebuggerAnalysis,
    QueryResult,
    SQLQuery,
    ValidationResult,
)


class AgentState(TypedDict):
    """State shared across all nodes in the SQL agent graph.

    Attributes
    ----------
    user_question : str
        The natural-language question provided by the user.
        *Set by*: ``run_agent`` (initial state).
    dialect : str
        Target SQL dialect (MySQL, PostgreSQL, SQLite, SQL Server, Oracle).
        *Set by*: ``run_agent`` (initial state).
    db_schema : str
        Database schema string extracted via ``DatabaseManager.get_schema``.
        *Set by*: ``sql_planner``.
    generated_sql : SQLQuery | None
        The structured SQL query produced by the Planner (or Debugger on retry).
        *Set by*: ``sql_planner``, ``debugger_node``.
    execution_result : QueryResult | None
        Result of executing the SQL against the database.
        *Set by*: ``sql_executor_node``.
    validation_result : ValidationResult | None
        Validator output — is_valid flag, issues, and suggestions.
        *Set by*: ``result_validator``.
    debugger_analysis : DebuggerAnalysis | None
        Root-cause analysis and corrected query from the Debugger.
        *Set by*: ``debugger_node``.
    requires_human_approval : bool
        ``True`` when the generated query is sensitive (DML/DDL).
        *Set by*: ``sql_planner``.
    human_approved : bool
        ``True`` when the user approves a sensitive query.
        *Set by*: ``human_approval``.
    retry_count : int
        Number of debug-retry cycles executed so far.
        *Set by*: ``debugger_node``.
    max_retries : int
        Retry budget (default 3).
        *Set by*: ``run_agent`` (initial state).
    final_answer : str | None
        Natural-language answer generated from validated results.
        *Set by*: ``generate_answer_node``.
    messages : list
        LangGraph message accumulator (uses ``add_messages`` reducer).
        *Appended by*: all nodes.
    """

    # User input
    user_question: str
    dialect: Literal["MySQL", "PostgreSQL", "SQLite", "SQL Server", "Oracle"]

    # Database context
    db_schema: str

    # SQL generation
    generated_sql: Optional[SQLQuery]

    # Execution
    execution_result: Optional[QueryResult]

    # Validation
    validation_result: Optional[ValidationResult]

    # Debugging
    debugger_analysis: Optional[DebuggerAnalysis]

    # Control flow
    requires_human_approval: bool
    human_approved: bool
    retry_count: int
    max_retries: int
    final_answer: Optional[str]
    messages: Annotated[list, add_messages]
