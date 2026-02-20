"""
Unit tests for the QueryCache.

Run::

    pytest tests/test_cache.py -v
"""

from src.db.cache import QueryCache
from src.models.schemas import QueryResult


class TestQueryCache:
    """Tests for QueryCache LRU behaviour."""

    def _make_result(self, n: int = 1) -> QueryResult:
        return QueryResult(success=True, data=[{"id": i} for i in range(n)], row_count=n)

    def test_put_and_get(self):
        cache = QueryCache()
        result = self._make_result()
        cache.put("MySQL", "SELECT 1", result)
        cached = cache.get("MySQL", "SELECT 1")
        assert cached is not None
        assert cached.row_count == 1

    def test_miss_returns_none(self):
        cache = QueryCache()
        assert cache.get("MySQL", "SELECT 999") is None

    def test_hit_miss_counters(self):
        cache = QueryCache()
        cache.get("MySQL", "SELECT 1")  # miss
        cache.put("MySQL", "SELECT 1", self._make_result())
        cache.get("MySQL", "SELECT 1")  # hit
        assert cache.hits == 1
        assert cache.misses == 1

    def test_failed_queries_not_cached(self):
        cache = QueryCache()
        failed = QueryResult(success=False, error_message="err", row_count=0)
        cache.put("MySQL", "SELECT bad", failed)
        assert cache.get("MySQL", "SELECT bad") is None

    def test_normalisation(self):
        """Queries differing only in whitespace/case should share a key."""
        cache = QueryCache()
        result = self._make_result()
        cache.put("MySQL", "SELECT  1", result)
        cached = cache.get("MySQL", "select 1")
        assert cached is not None

    def test_eviction_on_size_limit(self):
        cache = QueryCache(max_size_bytes=500)  # tiny limit
        for i in range(100):
            cache.put("MySQL", f"SELECT {i}", self._make_result(5))
        # Should have evicted most entries
        assert cache.current_size_bytes <= 500

    def test_clear(self):
        cache = QueryCache()
        cache.put("MySQL", "SELECT 1", self._make_result())
        cache.get("MySQL", "SELECT 1")
        cache.clear()
        assert cache.stats()["entries"] == 0
        assert cache.hits == 0

    def test_stats_format(self):
        cache = QueryCache()
        stats = cache.stats()
        assert "entries" in stats
        assert "hit_rate" in stats
        assert stats["hit_rate"] == "N/A"
