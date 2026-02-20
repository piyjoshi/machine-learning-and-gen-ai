"""
Pydantic models for the Self-Correcting SQL Agent.

This module defines all structured output schemas used by the LLM and
the agent pipeline.  Each model maps to a specific stage:

- **SQLQuery** — Planner output (generated SQL + metadata)
- **QueryResult** — Executor output (rows / error)
- **ValidationResult** — Validator output (issues / suggestions)
- **DebuggerAnalysis** — Debugger output (root-cause + corrected SQL)

Example
-------
>>> from src.models.schemas import SQLQuery
>>> q = SQLQuery(
...     query="SELECT * FROM users WHERE active = 1",
...     explanation="Fetch all active users",
...     is_sensitive=False,
...     dialect="MySQL",
... )
>>> q.is_sensitive
False
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SQLQuery(BaseModel):
    """Generated SQL query and its metadata.

    Attributes
    ----------
    query : str
        The SQL statement to be executed.
    explanation : str
        Human-readable explanation of what the query does.
    is_sensitive : bool
        ``True`` when the query modifies data (DELETE, UPDATE, DROP, …).
    dialect : str
        Target SQL dialect (MySQL, PostgreSQL, SQLite, SQL Server, Oracle).

    Example
    -------
    >>> q = SQLQuery(
    ...     query="DELETE FROM logs WHERE created_at < '2024-01-01'",
    ...     explanation="Purge old log entries",
    ...     is_sensitive=True,
    ...     dialect="PostgreSQL",
    ... )
    >>> q.is_sensitive
    True
    """

    query: str = Field(description="The SQL query to be executed.")
    explanation: str = Field(description="Explanation of what the query does")
    is_sensitive: bool = Field(
        description="Whether the query modifies data (DELETE, UPDATE, DROP)"
    )
    dialect: Literal["MySQL", "PostgreSQL", "SQLite", "SQL Server", "Oracle"] = Field(
        description="The SQL dialect of the query.",
        default="MySQL",
    )


class QueryResult(BaseModel):
    """Result of a SQL query execution.

    Attributes
    ----------
    success : bool
        Whether the query executed without errors.
    data : list[dict] | None
        List of row dictionaries (``None`` on failure).
    error_message : str | None
        Error description when ``success`` is ``False``.
    row_count : int
        Number of rows returned / affected.

    Example
    -------
    >>> r = QueryResult(success=True, data=[{"id": 1, "name": "Alice"}], row_count=1)
    >>> r.row_count
    1
    """

    success: bool = Field(description="Whether the query executed successfully.")
    data: Optional[List[dict]] = None
    error_message: Optional[str] = None
    row_count: int = 0


class ValidationResult(BaseModel):
    """Validation analysis of query results.

    Attributes
    ----------
    is_valid : bool
        ``True`` when the results correctly answer the user's question.
    issues : list[str]
        Problems detected (empty results, wrong aggregation, …).
    suggestions : list[str]
        Recommended fixes.

    Example
    -------
    >>> v = ValidationResult(is_valid=False, issues=["Empty result set"], suggestions=["Check WHERE clause"])
    >>> v.is_valid
    False
    """

    is_valid: bool
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class DebuggerAnalysis(BaseModel):
    """Debugger analysis output for failed queries.

    Attributes
    ----------
    root_cause : str
        Identified root cause of the failure.
    corrected_query : str
        Fixed SQL query ready for re-execution.
    changes_made : list[str]
        Human-readable list of changes applied.

    Example
    -------
    >>> d = DebuggerAnalysis(
    ...     root_cause="Missing GROUP BY clause",
    ...     corrected_query="SELECT dept, COUNT(*) FROM emp GROUP BY dept",
    ...     changes_made=["Added GROUP BY dept"],
    ... )
    >>> d.root_cause
    'Missing GROUP BY clause'
    """

    root_cause: str
    corrected_query: str
    changes_made: List[str]
