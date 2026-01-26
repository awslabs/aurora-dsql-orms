# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg
from sqlalchemy.engine.interfaces import DBAPIModule

from .base import AuroraDSQLDialect


class AuroraDSQLDialect_psycopg(PGDialect_psycopg, AuroraDSQLDialect):
    driver = "psycopg"  # driver name
    supports_statement_cache = True

    @classmethod
    def import_dbapi(cls) -> DBAPIModule:  # type: ignore[override]
        # PGDialect_psycopg returns the psycopg module, but SQLAlchemy's base
        # Dialect expects DBAPIModule. The types are compatible at runtime but
        # differ in their type stubs.
        return super().import_dbapi()  # type: ignore[return-value]

    def detect_autocommit_setting(self, dbapi_conn: Any) -> bool:  # type: ignore[override]
        # Override resolves parameter name mismatch
        return super().detect_autocommit_setting(dbapi_connection=dbapi_conn)

    def get_isolation_level_values(self, dbapi_conn: Any) -> tuple[str, ...]:  # type: ignore[override]
        # Override resolves parameter name mismatch
        return super().get_isolation_level_values(dbapi_connection=dbapi_conn)

    # This disables the native hstore support. When enabled, this feature
    # checks if the hstore feature is available. During this check, a savepoint
    # is created which causes an error in DSQL.
    def __init__(self, **kwargs):
        kwargs.setdefault("use_native_hstore", False)
        super().__init__(**kwargs)
