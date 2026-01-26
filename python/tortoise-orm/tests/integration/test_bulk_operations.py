# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class BulkItem(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100, unique=True)
    value = fields.IntField(default=0)

    class Meta:
        table = "test_bulk_item"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestBulkOperations:
    async def test_bulk_create(self, backend):
        """Test bulk_create inserts multiple records."""
        items = [BulkItem(name=f"Item{i}") for i in range(5)]
        await BulkItem.bulk_create(items)
        assert await BulkItem.all().count() == 5

    async def test_bulk_create_empty(self, backend):
        """Test bulk_create with empty list."""
        await BulkItem.bulk_create([])
        assert await BulkItem.all().count() == 0

    async def test_bulk_update(self, backend):
        """Test bulk_update modifies multiple records."""
        items = [BulkItem(name=f"Item{i}", value=i) for i in range(3)]
        await BulkItem.bulk_create(items)
        all_items = await BulkItem.all()
        for item in all_items:
            item.value = 99
        await BulkItem.bulk_update(all_items, fields=["value"])
        updated = await BulkItem.all()
        assert all(i.value == 99 for i in updated)

    async def test_bulk_create_batch_size(self, backend):
        """Test bulk_create with batch_size."""
        items = [BulkItem(name=f"Item{i}") for i in range(10)]
        await BulkItem.bulk_create(items, batch_size=3)
        assert await BulkItem.all().count() == 10

    async def test_bulk_create_on_conflict_update(self, backend):
        """Test bulk_create with on_conflict for atomic upsert."""
        await BulkItem.bulk_create([BulkItem(name="upsert", value=1)])
        await BulkItem.bulk_create(
            [BulkItem(name="upsert", value=2)],
            on_conflict=["name"],
            update_fields=["value"],
        )
        item = await BulkItem.get(name="upsert")
        assert item.value == 2
        assert await BulkItem.filter(name="upsert").count() == 1
