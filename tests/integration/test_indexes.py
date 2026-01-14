# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid
from collections.abc import Sequence

import pytest
from tortoise import Tortoise, fields
from tortoise.indexes import Index
from tortoise.models import Model

from tests.conftest import BACKENDS


class IndexTestModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=100)

    class Meta:
        table = "index_test_model"
        indexes = [Index(fields=["name"])]


class UniqueIndexTestModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    code = fields.CharField(max_length=50, unique=True)

    class Meta:
        table = "unique_index_test_model"


async def get_indexes(table_name: str) -> Sequence[dict]:
    conn = Tortoise.get_connection("default")
    result = await conn.execute_query(
        f"SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '{table_name}'"
    )
    return result[1]


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
async def test_regular_index_created(backend: str):
    """Test that regular indexes are created with ASYNC keyword."""
    indexes = await get_indexes("index_test_model")
    index_names = [idx["indexname"] for idx in indexes]

    assert any("name" in name for name in index_names)


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
async def test_unique_index_created(backend: str):
    """Test that unique indexes are created with ASYNC keyword."""
    indexes = await get_indexes("unique_index_test_model")
    index_defs = [idx["indexdef"] for idx in indexes]

    assert any("UNIQUE" in defn and "code" in defn for defn in index_defs)
