# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy.engine.interfaces import DBAPIModule

from .base import AuroraDSQLDialect


class AuroraDSQLDialect_psycopg2(PGDialect_psycopg2, AuroraDSQLDialect):
    driver = "psycopg2"  # driver name
    supports_statement_cache = True

    @classmethod
    def import_dbapi(cls) -> DBAPIModule:  # type: ignore[override]
        # PGDialect_psycopg2 returns the psycopg2 module, but SQLAlchemy's base
        # Dialect expects DBAPIModule. The types are compatible at runtime but
        # differ in their type stubs.
        return super().import_dbapi()  # type: ignore[return-value]

    def detect_autocommit_setting(self, dbapi_conn: Any) -> bool:  # type: ignore[override]
        # Override resolves parameter name mismatch
        return super().detect_autocommit_setting(dbapi_connection=dbapi_conn)

    def get_isolation_level_values(self, dbapi_conn: Any) -> tuple[str, ...]:  # type: ignore[override]
        # Override resolves parameter name mismatch
        return super().get_isolation_level_values(dbapi_connection=dbapi_conn)
