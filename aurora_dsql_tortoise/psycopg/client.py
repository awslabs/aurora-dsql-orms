# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import warnings

import aurora_dsql_psycopg as dsql
import psycopg
import psycopg.conninfo
from tortoise.backends.psycopg.client import (
    AsyncConnectionPool,
    PsycopgClient,
)

from aurora_dsql_tortoise.common.config import DSQL_CONNECTOR_PARAMS
from aurora_dsql_tortoise.psycopg.schema_generator import AuroraDSQLPsycopgSchemaGenerator


class AuroraDSQLPsycopgClient(PsycopgClient):
    """Psycopg client adapted for Aurora DSQL compatibility."""

    schema_generator = AuroraDSQLPsycopgSchemaGenerator

    def __init__(self, *, database: str | None = "postgres", **kwargs):
        # Database is set for internal Tortoise usage. Connection defaults are
        # otherwise provided by the DSQL connector.
        super().__init__(database=database, **kwargs)

    async def create_pool(self, **kwargs) -> AsyncConnectionPool:
        conninfo = kwargs.pop("conninfo", "")

        # Psycopg allows the pool to be configured with connection-specific
        # kwargs which are nested within the pool kwargs.
        conn_kwargs = kwargs.pop("kwargs", {})

        # Parent class hardcodes psycopg.AsyncConnection, treat it as default.
        connection_class = kwargs.pop("connection_class", psycopg.AsyncConnection)
        if connection_class is None or connection_class is psycopg.AsyncConnection:
            connection_class = dsql.DSQLAsyncConnection
        elif not issubclass(connection_class, dsql.DSQLAsyncConnection):
            warnings.warn(
                f"{connection_class.__name__} is not a subclass of DSQLAsyncConnection. "
                "DSQL authentication may not work correctly.",
                UserWarning,
                stacklevel=2,
            )

        # Merge parsed conninfo into connection-specific kwargs.
        conn_kwargs.update(psycopg.conninfo.conninfo_to_dict(conninfo))

        # Only pass DSQL connector params to connection kwargs, not pool.
        for key in DSQL_CONNECTOR_PARAMS:
            if key in kwargs:
                conn_kwargs[key] = kwargs.pop(key)
            elif key in self.extra:
                conn_kwargs[key] = self.extra[key]

        pool = AsyncConnectionPool(
            "",
            connection_class=connection_class,
            kwargs=conn_kwargs,
            open=False,
            **kwargs,
        )
        await pool.open()
        return pool
