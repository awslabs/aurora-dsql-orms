# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator

from aurora_dsql_tortoise.common.config import split_sql
from aurora_dsql_tortoise.common.schema_generator import AuroraDSQLSchemaGeneratorMixin


class AuroraDSQLAsyncpgSchemaGenerator(AuroraDSQLSchemaGeneratorMixin, AsyncpgSchemaGenerator):
    """Asyncpg schema generator adapted for Aurora DSQL compatibility."""

    async def generate_from_string(self, creation_string: str) -> None:
        async with self.client.acquire_connection() as connection:
            # Transactions in Aurora DSQL can contain only one DDL statement.
            for command in split_sql(creation_string):
                await connection.execute(command)
