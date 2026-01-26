# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid

import pytest
from tortoise import Tortoise, fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class Author(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "test_author"


class Book(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    title = fields.CharField(max_length=200)
    author = fields.ForeignKeyField("models.Author", related_name="books")

    class Meta:
        table = "test_book"


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
async def test_multiple_ddl_statements(backend: str):
    """Test that generate_schemas correctly splits and executes multiple DDL statements."""
    await Tortoise.generate_schemas()
    conn = Tortoise.get_connection("default")
    result = await conn.execute_query(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name IN ('test_author', 'test_book')"
    )
    tables = {row["table_name"] for row in result[1]}
    assert tables == {"test_author", "test_book"}, f"Expected both tables, got: {tables}"
