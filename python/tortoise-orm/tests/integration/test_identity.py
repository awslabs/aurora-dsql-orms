# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for BigIntField identity columns."""

import pytest
from tortoise import Tortoise, fields
from tortoise.models import Model

from aurora_dsql_tortoise.common import fields as dsql_fields
from tests.conftest import BACKENDS


class BigIntPKModel(Model):
    id = fields.BigIntField(primary_key=True)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "test_bigint_pk"


class CustomCachePKModel(Model):
    id = dsql_fields.BigIntField(primary_key=True, sequence_cache_size=1)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "test_custom_cache_pk"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestBigIntIdentity:
    """Tests for BigIntField identity column support."""

    async def test_insert_returns_generated_id(self, backend):
        """Test that insert returns auto-generated ID."""
        obj = await BigIntPKModel.create(name="test1")
        assert obj.id is not None
        assert isinstance(obj.id, int)

    async def test_insert_with_explicit_id(self, backend):
        """Test that explicit ID is accepted ."""
        obj = await BigIntPKModel.create(id=999999, name="explicit")
        assert obj.id == 999999

    async def test_multiple_inserts_get_unique_ids(self, backend):
        """Test that multiple inserts get unique IDs."""
        obj1 = await BigIntPKModel.create(name="first")
        obj2 = await BigIntPKModel.create(name="second")
        obj3 = await BigIntPKModel.create(name="third")

        ids = {obj1.id, obj2.id, obj3.id}
        assert len(ids) == 3, "All IDs should be unique"

    async def test_bulk_create_returns_ids(self, backend):
        """Test that bulk create returns generated IDs."""
        objects = [BigIntPKModel(name=f"bulk{i}") for i in range(5)]
        await BigIntPKModel.bulk_create(objects)

        # Refresh to get IDs.
        all_objs = await BigIntPKModel.filter(name__startswith="bulk").all()
        assert len(all_objs) == 5
        ids = {obj.id for obj in all_objs}
        assert len(ids) == 5, "All bulk created objects should have unique IDs"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestCustomCacheField:
    """Tests for custom BigIntField with configurable cache."""

    async def test_custom_cache_size_applied(self, backend):
        """Test that custom sequence_cache_size is correctly applied to the identity column."""
        conn = Tortoise.get_connection("default")
        result = await conn.execute_query(
            "SELECT cache_size FROM pg_sequences WHERE sequencename = 'test_custom_cache_pk_id_seq'"
        )
        assert len(result[1]) == 1, "Sequence should exist"
        assert result[1][0]["cache_size"] == 1, "Cache size should be 1"

    async def test_custom_cache_insert(self, backend):
        """Test that custom cache field works for inserts."""
        obj = await CustomCachePKModel.create(name="cache1")
        assert obj.id is not None
        assert isinstance(obj.id, int)
