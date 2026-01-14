# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise.backends.base_postgres.schema_generator import BasePostgresSchemaGenerator

if TYPE_CHECKING:
    from tortoise.backends.base.schema_generator import BaseSchemaGenerator
    from tortoise.backends.base_postgres.client import BasePostgresClient

    _Base = BaseSchemaGenerator
else:
    _Base = object


class AuroraDSQLSchemaGeneratorMixin(_Base):
    """Adapts schema generation for DSQL."""

    client: BasePostgresClient
    INDEX_CREATE_TEMPLATE = (
        'CREATE INDEX ASYNC {exists}"{index_name}" ON "{table_name}" {index_type}({fields}){extra};'
    )
    UNIQUE_INDEX_CREATE_TEMPLATE = INDEX_CREATE_TEMPLATE.replace("INDEX", "UNIQUE INDEX")

    def _create_fk_string(
        self,
        constraint_name: str,
        db_column: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        """Return empty string since DSQL doesn't support foreign key constraints.

        Foreign keys can still be defined in Tortoise models for ORM relationships,
        but the constraints are not forwarded to the database.
        """
        return ""


class AuroraDSQLBaseSchemaGenerator(AuroraDSQLSchemaGeneratorMixin, BasePostgresSchemaGenerator):
    """Base schema generator for Aurora DSQL, used by aerich for DDL generation
    without driver-specific dependencies."""

    pass
