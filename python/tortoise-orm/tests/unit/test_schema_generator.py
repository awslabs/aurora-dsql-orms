# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid
from unittest.mock import MagicMock

import pytest
from tortoise import Tortoise, fields
from tortoise.models import Model

from aurora_dsql_tortoise.asyncpg.schema_generator import AuroraDSQLAsyncpgSchemaGenerator
from aurora_dsql_tortoise.psycopg.schema_generator import AuroraDSQLPsycopgSchemaGenerator


class Parent(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100, db_index=True)

    class Meta:
        table = "test_parent"


class Child(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    parent = fields.ForeignKeyField("models.Parent", related_name="children")

    class Meta:
        table = "test_child"


@pytest.fixture
async def initialized_models():
    """Initialize Tortoise with models but no real DB connection."""
    await Tortoise.init(
        config={
            "connections": {"default": "sqlite://:memory:"},
            "apps": {"models": {"models": [__name__], "default_connection": "default"}},
        }
    )
    yield
    await Tortoise.close_connections()


def _create_mock_client():
    """Create a mock client that matches the default connection for model filtering."""
    connection = Tortoise.get_connection("default")
    mock_client = MagicMock()
    mock_client.schema = None
    type(mock_client).__eq__ = lambda self, other: other == connection
    return mock_client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "generator_cls", [AuroraDSQLPsycopgSchemaGenerator, AuroraDSQLAsyncpgSchemaGenerator]
)
async def test_schema_excludes_fk_references(initialized_models, generator_cls):
    """Test that generated schema SQL does not contain FK REFERENCES clause."""
    generator = generator_cls(_create_mock_client())
    schema_sql = generator.get_create_schema_sql(safe=True)

    assert "parent_id" in schema_sql, f"Schema should contain FK column:\n{schema_sql}"
    assert "REFERENCES" not in schema_sql, f"Schema should not contain FK REFERENCES:\n{schema_sql}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "generator_cls", [AuroraDSQLPsycopgSchemaGenerator, AuroraDSQLAsyncpgSchemaGenerator]
)
async def test_schema_uses_async_index_creation(initialized_models, generator_cls):
    """Test that CREATE INDEX statements use ASYNC keyword for DSQL."""
    generator = generator_cls(_create_mock_client())
    schema_sql = generator.get_create_schema_sql(safe=True)

    assert "CREATE INDEX ASYNC" in schema_sql, (
        f"Schema should use ASYNC index creation:\n{schema_sql}"
    )
