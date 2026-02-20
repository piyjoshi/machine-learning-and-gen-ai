"""
LRU query cache with SHA-256 key hashing and memory-bounded eviction.

This module provides a thread-safe (single-process) LRU cache that stores
successful SQL query results keyed by ``SHA-256(dialect + normalized_sql)``.

The cache automatically evicts least-recently-used entries when the
configurable memory limit is reached (default **100 MB**).

Example
-------
>>> from src.db.cache import QueryCache
>>> from src.models.schemas import QueryResult
>>>
>>> cache = QueryCache(max_size_bytes=50 * 1024 * 1024)  # 50 MB
>>> result = QueryResult(success=True, data=[{"id": 1}], row_count=1)
>>>
>>> cache.put("MySQL", "SELECT 1", result)
>>> cached = cache.get("MySQL", "SELECT 1")
>>> cached.row_count
1
>>> cache.stats()
{'entries': 1, 'size_mb': ..., 'max_size_mb': 47.68, 'hits': 1, 'misses': 0, 'hit_rate': '100.0%'}
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import OrderedDict
from typing import Optional

from src.models.schemas import QueryResult


class QueryCache:
    """LRU cache for SQL query results with a max size limit.

    Parameters
    ----------
    max_size_bytes : int, default ``100 * 1024 * 1024`` (100 MB)
        Maximum total memory the cache is allowed to occupy.
        When this limit is exceeded the least-recently-used entries
        are evicted until there is room for the new entry.

    Attributes
    ----------
    hits : int
        Number of cache hits since creation / last ``clear()``.
    misses : int
        Number of cache misses.

    Example
    -------
    >>> cache = QueryCache(max_size_bytes=1024)
    >>> cache.stats()["entries"]
    0
    """

    def __init__(self, max_size_bytes: int = 100 * 1024 * 1024) -> None:
        self.max_size_bytes = max_size_bytes
        self.current_size_bytes = 0
        self._cache: OrderedDict[str, tuple[QueryResult, int]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_key(self, dialect: str, sql_query: str) -> str:
        """Create a unique cache key from dialect + normalised SQL.

        The SQL is lowered, whitespace-collapsed, then hashed with SHA-256
        to produce a fixed-length key regardless of query length.

        Parameters
        ----------
        dialect : str
            Database dialect (e.g. ``"MySQL"``).
        sql_query : str
            Raw SQL string.

        Returns
        -------
        str
            64-character hex digest.
        """
        normalised = " ".join(sql_query.strip().lower().split())
        raw = f"{dialect}::{normalised}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _estimate_size(self, result: QueryResult) -> int:
        """Estimate the memory size of a ``QueryResult`` in bytes.

        Uses ``sys.getsizeof`` on the JSON-serialised payload.
        """
        return sys.getsizeof(json.dumps(result.model_dump(), default=str))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, dialect: str, sql_query: str) -> Optional[QueryResult]:
        """Retrieve a cached result.

        On a hit the entry is moved to the *end* (most-recently-used).

        Parameters
        ----------
        dialect : str
            Database dialect.
        sql_query : str
            SQL query string.

        Returns
        -------
        QueryResult or None
            Cached result on hit, ``None`` on miss.
        """
        key = self._make_key(dialect, sql_query)
        if key in self._cache:
            self._cache.move_to_end(key)
            self.hits += 1
            return self._cache[key][0]
        self.misses += 1
        return None

    def put(self, dialect: str, sql_query: str, result: QueryResult) -> None:
        """Store a result in the cache.

        - Failed queries (``success=False``) are **not** cached.
        - If a single entry exceeds ``max_size_bytes`` it is silently
          skipped.
        - Existing entries for the same key are replaced.

        Parameters
        ----------
        dialect : str
            Database dialect.
        sql_query : str
            SQL query string.
        result : QueryResult
            Execution result to cache.
        """
        if not result.success:
            return

        key = self._make_key(dialect, sql_query)
        entry_size = self._estimate_size(result)

        if entry_size > self.max_size_bytes:
            return

        # Replace existing entry
        if key in self._cache:
            _, old_size = self._cache.pop(key)
            self.current_size_bytes -= old_size

        # Evict LRU entries until there is room
        while (
            self.current_size_bytes + entry_size > self.max_size_bytes
            and self._cache
        ):
            _, (_, evicted_size) = self._cache.popitem(last=False)
            self.current_size_bytes -= evicted_size

        self._cache[key] = (result, entry_size)
        self.current_size_bytes += entry_size

    def clear(self) -> None:
        """Flush the entire cache and reset hit/miss counters."""
        self._cache.clear()
        self.current_size_bytes = 0
        self.hits = 0
        self.misses = 0

    def stats(self) -> dict:
        """Return cache statistics.

        Returns
        -------
        dict
            Keys: ``entries``, ``size_mb``, ``max_size_mb``, ``hits``,
            ``misses``, ``hit_rate``.

        Example
        -------
        >>> cache = QueryCache()
        >>> cache.stats()["hit_rate"]
        'N/A'
        """
        total = self.hits + self.misses
        return {
            "entries": len(self._cache),
            "size_mb": round(self.current_size_bytes / (1024 * 1024), 2),
            "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": (
                f"{(self.hits / total * 100):.1f}%" if total > 0 else "N/A"
            ),
        }
