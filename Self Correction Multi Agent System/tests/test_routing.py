"""
Unit tests for routing / decision functions.

Run::

    pytest tests/test_routing.py -v
"""

from langgraph.graph import END

from src.models.schemas import QueryResult, ValidationResult
from src.routing.decisions import (
    check_approval_results,
    should_get_approval,
    should_retry_or_complete,
)


class TestShouldGetApproval:

    def test_sensitive_routes_to_approval(self):
        assert should_get_approval({"requires_human_approval": True}) == "human_approval"

    def test_non_sensitive_routes_to_executor(self):
        assert should_get_approval({"requires_human_approval": False}) == "executor"

    def test_missing_key_defaults_to_executor(self):
        assert should_get_approval({}) == "executor"


class TestCheckApprovalResults:

    def test_approved(self):
        assert check_approval_results({"human_approved": True}) == "executor"

    def test_rejected(self):
        assert check_approval_results({"human_approved": False}) == END


class TestShouldRetryOrComplete:

    def test_valid_result_routes_to_answer(self):
        state = {
            "execution_result": QueryResult(success=True, row_count=5),
            "validation_result": ValidationResult(is_valid=True),
            "retry_count": 0,
            "max_retries": 3,
        }
        assert should_retry_or_complete(state) == "answer"

    def test_invalid_with_retries_routes_to_debugger(self):
        state = {
            "execution_result": QueryResult(success=True, row_count=0),
            "validation_result": ValidationResult(is_valid=False, issues=["empty"]),
            "retry_count": 1,
            "max_retries": 3,
        }
        assert should_retry_or_complete(state) == "debugger"

    def test_retries_exhausted_routes_to_end(self):
        state = {
            "execution_result": QueryResult(success=False, error_message="err"),
            "validation_result": ValidationResult(is_valid=False),
            "retry_count": 3,
            "max_retries": 3,
        }
        assert should_retry_or_complete(state) == "end"

    def test_execution_failure_with_budget(self):
        state = {
            "execution_result": QueryResult(success=False, error_message="err"),
            "validation_result": None,
            "retry_count": 0,
            "max_retries": 3,
        }
        assert should_retry_or_complete(state) == "debugger"
