"""
Unit tests for Pydantic schemas.

Run::

    pytest tests/test_schemas.py -v
"""

import pytest

from src.models.schemas import (
    DebuggerAnalysis,
    QueryResult,
    SQLQuery,
    ValidationResult,
)


class TestSQLQuery:
    """Tests for the SQLQuery model."""

    def test_basic_creation(self):
        q = SQLQuery(
            query="SELECT 1",
            explanation="Test query",
            is_sensitive=False,
            dialect="MySQL",
        )
        assert q.query == "SELECT 1"
        assert q.is_sensitive is False

    def test_sensitive_flag(self):
        q = SQLQuery(
            query="DROP TABLE users",
            explanation="Drop users table",
            is_sensitive=True,
            dialect="PostgreSQL",
        )
        assert q.is_sensitive is True

    def test_default_dialect(self):
        q = SQLQuery(
            query="SELECT 1",
            explanation="test",
            is_sensitive=False,
        )
        assert q.dialect == "MySQL"

    def test_invalid_dialect_rejected(self):
        with pytest.raises(Exception):
            SQLQuery(
                query="SELECT 1",
                explanation="test",
                is_sensitive=False,
                dialect="MongoDB",  # not a valid literal
            )


class TestQueryResult:
    """Tests for the QueryResult model."""

    def test_success(self):
        r = QueryResult(success=True, data=[{"id": 1}], row_count=1)
        assert r.success is True
        assert r.row_count == 1

    def test_failure(self):
        r = QueryResult(success=False, error_message="syntax error", row_count=0)
        assert r.success is False
        assert r.error_message == "syntax error"

    def test_defaults(self):
        r = QueryResult(success=True)
        assert r.data is None
        assert r.error_message is None
        assert r.row_count == 0


class TestValidationResult:
    """Tests for the ValidationResult model."""

    def test_valid(self):
        v = ValidationResult(is_valid=True)
        assert v.issues == []
        assert v.suggestions == []

    def test_invalid_with_issues(self):
        v = ValidationResult(
            is_valid=False,
            issues=["Empty result"],
            suggestions=["Check WHERE clause"],
        )
        assert len(v.issues) == 1


class TestDebuggerAnalysis:
    """Tests for the DebuggerAnalysis model."""

    def test_creation(self):
        d = DebuggerAnalysis(
            root_cause="Missing GROUP BY",
            corrected_query="SELECT dept, COUNT(*) FROM emp GROUP BY dept",
            changes_made=["Added GROUP BY dept"],
        )
        assert "GROUP BY" in d.corrected_query
        assert len(d.changes_made) == 1
