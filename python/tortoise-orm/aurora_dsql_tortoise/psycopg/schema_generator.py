# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from tortoise.backends.psycopg.schema_generator import PsycopgSchemaGenerator

from aurora_dsql_tortoise.common.config import split_sql
from aurora_dsql_tortoise.common.schema_generator import AuroraDSQLSchemaGeneratorMixin


class AuroraDSQLPsycopgSchemaGenerator(AuroraDSQLSchemaGeneratorMixin, PsycopgSchemaGenerator):
    """Psycopg schema generator adapted for Aurora DSQL compatibility."""

    async def generate_from_string(self, creation_string: str) -> None:
        async with self.client.acquire_connection() as connection:
            prev_auto_commit = connection.autocommit
            try:
                await connection.set_autocommit(True)
                # Transactions in Aurora DSQL can contain only one DDL statement.
                for command in split_sql(creation_string):
                    await connection.execute(command)
            finally:
                await connection.set_autocommit(prev_auto_commit)
