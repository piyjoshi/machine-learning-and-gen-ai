"""
Database connection manager with multi-dialect support.

``DatabaseManager`` lazily creates SQLAlchemy engines for every supported
dialect, introspects schemas, and executes queries — all integrated with
the :class:`~src.db.cache.QueryCache`.

Supported dialects
------------------
========== ============ ======================================
Dialect    Driver       Env var
========== ============ ======================================
MySQL      pymysql      ``MYSQL_CONNECTION_STRING``
PostgreSQL psycopg2     ``POSTGRESQL_CONNECTION_STRING``
SQLite     built-in     ``SQLITE_CONNECTION_STRING``
SQL Server pyodbc       ``SQLSERVER_CONNECTION_STRING``
Oracle     cx_oracle    ``ORACLE_CONNECTION_STRING``
========== ============ ======================================

Example
-------
>>> from src.db.manager import DatabaseManager
>>> db = DatabaseManager()
>>> schema = db.get_schema("SQLite")     # introspect tables & columns
>>> result, from_cache = db.execute_query("SQLite", "SELECT 1")
>>> result.success
True
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from src.db.cache import QueryCache
from src.models.schemas import QueryResult


# Default connection-string templates per dialect
_DEFAULT_CONNECTIONS: dict[str, str] = {
    "MySQL": "mysql+pymysql://user:password@localhost/dbname",
    "PostgreSQL": "postgresql+psycopg2://user:password@localhost/dbname",
    "SQLite": "sqlite:///./database.db",
    "SQL Server": (
        "mssql+pyodbc://user:password@localhost/dbname"
        "?driver=ODBC+Driver+17+for+SQL+Server"
    ),
    "Oracle": "oracle+cx_oracle://user:password@localhost:1521/dbname",
}

# Env-var names used for each dialect
_ENV_VAR_MAP: dict[str, str] = {
    "MySQL": "MYSQL_CONNECTION_STRING",
    "PostgreSQL": "POSTGRESQL_CONNECTION_STRING",
    "SQLite": "SQLITE_CONNECTION_STRING",
    "SQL Server": "SQLSERVER_CONNECTION_STRING",
    "Oracle": "ORACLE_CONNECTION_STRING",
}


class DatabaseManager:
    """Manage database engines, schema introspection, and cached query execution.

    Parameters
    ----------
    cache_size_bytes : int, default ``100 * 1024 * 1024``
        Maximum memory for the built-in LRU query cache.

    Attributes
    ----------
    engines : dict[str, Engine]
        Lazily-populated pool of SQLAlchemy engines keyed by dialect.
    cache : QueryCache
        LRU cache instance shared across all queries.

    Example
    -------
    >>> db = DatabaseManager(cache_size_bytes=50 * 1024 * 1024)
    >>> engine = db.get_engine("SQLite", "sqlite:///test.db")
    >>> type(engine).__name__
    'Engine'
    """

    def __init__(self, cache_size_bytes: int = 100 * 1024 * 1024) -> None:
        self.engines: dict = {}
        self.cache = QueryCache(max_size_bytes=cache_size_bytes)

    # ------------------------------------------------------------------
    # Engine management
    # ------------------------------------------------------------------

    def get_engine(self, dialect: str, connection_string: Optional[str] = None):
        """Get or create a SQLAlchemy engine for *dialect*.

        Resolution order:

        1. Reuse a previously created engine for this dialect.
        2. Use the explicit *connection_string* if provided.
        3. Read the env-var for that dialect (see ``_ENV_VAR_MAP``).
        4. Fall back to the built-in default template.

        Parameters
        ----------
        dialect : str
            One of ``MySQL``, ``PostgreSQL``, ``SQLite``,
            ``SQL Server``, ``Oracle``.
        connection_string : str or None
            Optional explicit connection string.

        Returns
        -------
        sqlalchemy.engine.Engine

        Raises
        ------
        ValueError
            If *dialect* is not supported and no *connection_string*
            was supplied.
        """
        if dialect in self.engines:
            return self.engines[dialect]

        if connection_string:
            engine = create_engine(connection_string)
        else:
            env_var = _ENV_VAR_MAP.get(dialect, "")
            cs = os.getenv(env_var, _DEFAULT_CONNECTIONS.get(dialect, ""))
            if not cs:
                raise ValueError(f"Unsupported SQL dialect: {dialect}")
            engine = create_engine(cs)

        self.engines[dialect] = engine
        return engine

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------

    def get_schema(self, dialect: str) -> str:
        """Extract a human-readable schema from the database.

        Includes table names, column names & types, primary keys, and
        foreign-key relationships.

        Parameters
        ----------
        dialect : str
            Target database dialect.

        Returns
        -------
        str
            Multi-line string describing all tables.
        """
        engine = self.get_engine(dialect)
        inspector = inspect(engine)

        schema_info: list[str] = []
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            col_info = [f"  - {col['name']}: {col['type']}" for col in columns]

            # Primary keys
            pk = inspector.get_pk_constraint(table_name)
            pk_cols = pk.get("constrained_columns", []) if pk else []

            # Foreign keys
            fks = inspector.get_foreign_keys(table_name)
            fk_info = [
                f"  FK: {fk['constrained_columns']} -> "
                f"{fk['referred_table']}.{fk['referred_columns']}"
                for fk in fks
            ]

            table_schema = f"Table: {table_name}\n"
            table_schema += f"  Primary Key: {pk_cols}\n"
            table_schema += "  Columns:\n" + "\n".join(col_info)
            if fk_info:
                table_schema += "\n  Foreign Keys:\n" + "\n".join(fk_info)

            schema_info.append(table_schema)

        return "\n\n".join(schema_info)

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    def execute_query(
        self, dialect: str, sql_query: str
    ) -> tuple[QueryResult, bool]:
        """Execute a SQL query and return ``(result, from_cache)``.

        The cache is checked first.  On a miss the query is run via
        SQLAlchemy and successful results are stored.

        Parameters
        ----------
        dialect : str
            Target dialect.
        sql_query : str
            Raw SQL statement.

        Returns
        -------
        tuple[QueryResult, bool]
            ``(result, from_cache)`` — the bool indicates a cache hit.

        Example
        -------
        >>> db = DatabaseManager()
        >>> res, cached = db.execute_query("SQLite", "SELECT 1 AS n")
        >>> res.success
        True
        """
        # Cache lookup
        cached = self.cache.get(dialect, sql_query)
        if cached is not None:
            return cached, True

        engine = self.get_engine(dialect)

        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql_query))

                if result.returns_rows:
                    rows = [dict(row._mapping) for row in result.fetchall()]
                    query_result = QueryResult(
                        success=True, data=rows, row_count=len(rows)
                    )
                else:
                    conn.commit()
                    query_result = QueryResult(
                        success=True, data=[], row_count=result.rowcount
                    )
        except SQLAlchemyError as exc:
            query_result = QueryResult(
                success=False, error_message=str(exc), row_count=0
            )

        # Cache successful results
        self.cache.put(dialect, sql_query, query_result)
        return query_result, False
