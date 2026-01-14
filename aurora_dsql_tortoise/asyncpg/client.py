# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncpg
import aurora_dsql_asyncpg as dsql
from tortoise.backends.asyncpg.client import AsyncpgDBClient

from aurora_dsql_tortoise.asyncpg.schema_generator import AuroraDSQLAsyncpgSchemaGenerator
from aurora_dsql_tortoise.common.config import DSQL_CONNECTOR_PARAMS


class AuroraDSQLAsyncpgClient(AsyncpgDBClient):
    """Asyncpg client adapted for Aurora DSQL compatibility."""

    schema_generator = AuroraDSQLAsyncpgSchemaGenerator

    def __init__(self, *, database: str | None = "postgres", **kwargs):
        # Database is set for internal Tortoise usage. Connection defaults are
        # otherwise provided by the DSQL connector.
        super().__init__(database=database, **kwargs)

    async def create_pool(self, **kwargs) -> asyncpg.Pool:
        for key in DSQL_CONNECTOR_PARAMS:
            if key not in kwargs and key in self.extra:
                kwargs[key] = self.extra[key]
        return await dsql.create_pool(None, **kwargs)
