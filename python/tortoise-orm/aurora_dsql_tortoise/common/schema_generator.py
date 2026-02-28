# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise.backends.base_postgres.schema_generator import BasePostgresSchemaGenerator
from tortoise.fields import Field

if TYPE_CHECKING:
    from tortoise.backends.base.schema_generator import BaseSchemaGenerator
    from tortoise.backends.base_postgres.client import BasePostgresClient

    _Base = BaseSchemaGenerator
else:
    _Base = object

from aurora_dsql_tortoise.common.fields import DEFAULT_SEQUENCE_CACHE_SIZE, _get_identity_sql


class AuroraDSQLSchemaGeneratorMixin(_Base):
    """Adapts schema generation for DSQL."""
    __table_name_clause = (
        '{table_name}'  # tortoise>=1.0.0
        if '"{table_name}"' not in BasePostgresSchemaGenerator.INDEX_CREATE_TEMPLATE
        else '"{table_name}"'  # tortoise<1.0.0
    )

    client: BasePostgresClient

    INDEX_CREATE_TEMPLATE = (
        'CREATE INDEX ASYNC {exists}"{index_name}" ON {table_name} {index_type}({fields}){extra};'.replace(
            '{table_name}',
            __table_name_clause,
        )
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

    def _get_pk_create_sql(self, field_object: Field, column_name: str, comment: str) -> str:
        """Override to use IDENTITY instead of SERIAL for generated integer PKs.

        DSQL only supports BIGINT for identity columns.
        """
        if field_object.pk and field_object.generated:
            if field_object.SQL_TYPE == "BIGINT":
                generated_sql = field_object.get_for_dialect(self.DIALECT, "GENERATED_SQL")
                if "BIGSERIAL" in generated_sql:
                    generated_sql = _get_identity_sql(DEFAULT_SEQUENCE_CACHE_SIZE)
                return self.GENERATED_PK_TEMPLATE.format(
                    field_name=column_name,
                    generated_sql=generated_sql,
                    comment=comment,
                )
            if field_object.SQL_TYPE in ("INT", "SMALLINT"):
                raise ValueError(
                    f"Aurora DSQL does not support {field_object.__class__.__name__} as an "
                    f"auto-generated primary key. Use UUIDField(primary_key=True) (recommended) "
                    f"or BigIntField(primary_key=True) instead."
                )
        return super()._get_pk_create_sql(field_object, column_name, comment)


class AuroraDSQLBaseSchemaGenerator(AuroraDSQLSchemaGeneratorMixin, BasePostgresSchemaGenerator):
    """Base schema generator for Aurora DSQL, used by aerich for DDL generation
    without driver-specific dependencies."""

    pass
