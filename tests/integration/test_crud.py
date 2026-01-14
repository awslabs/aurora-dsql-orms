# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class Item(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100)
    description = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "test_item"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestCRUD:
    async def test_create(self, backend):
        """Test creating a record."""
        item = await Item.create(name="Test", description="A test item")
        assert item.id is not None
        assert item.name == "Test"

    async def test_read(self, backend):
        """Test reading records."""
        created = await Item.create(name="ReadTest")
        fetched = await Item.get(id=created.id)
        assert fetched.name == "ReadTest"

    async def test_update(self, backend):
        """Test updating a record."""
        item = await Item.create(name="Original")
        item.name = "Updated"
        await item.save()
        fetched = await Item.get(id=item.id)
        assert fetched.name == "Updated"

    async def test_delete(self, backend):
        """Test deleting a record."""
        item = await Item.create(name="ToDelete")
        item_id = item.id
        await item.delete()
        assert await Item.filter(id=item_id).count() == 0

    async def test_filter(self, backend):
        """Test filtering records."""
        await Item.create(name="Alpha")
        await Item.create(name="Beta")
        await Item.create(name="Alpha")
        results = await Item.filter(name="Alpha").all()
        assert len(results) == 2

    async def test_get_or_none(self, backend):
        """Test get_or_none returns None for missing record."""
        result = await Item.get_or_none(id=uuid.uuid4())
        assert result is None

    async def test_update_from_dict(self, backend):
        """Test updating record from dict."""
        item = await Item.create(name="Original", description="Old")
        await item.update_from_dict({"name": "New", "description": "Updated"}).save()
        fetched = await Item.get(id=item.id)
        assert fetched.name == "New"
        assert fetched.description == "Updated"

    async def test_count(self, backend):
        """Test counting records."""
        await Item.create(name="One")
        await Item.create(name="Two")
        count = await Item.all().count()
        assert count == 2

    async def test_exists(self, backend):
        """Test exists check."""
        await Item.create(name="Exists")
        assert await Item.filter(name="Exists").exists()
        assert not await Item.filter(name="NotExists").exists()

    async def test_get_or_create(self, backend):
        """Test get_or_create."""
        item1, created1 = await Item.get_or_create(name="Unique", defaults={"description": "First"})
        assert created1
        item2, created2 = await Item.get_or_create(
            name="Unique", defaults={"description": "Second"}
        )
        assert not created2
        assert item1.id == item2.id

    async def test_first_last(self, backend):
        """Test first and last."""
        await Item.create(name="A")
        await Item.create(name="B")
        first = await Item.all().order_by("name").first()
        last = await Item.all().order_by("name").last()
        assert first is not None
        assert last is not None
        assert first.name == "A"
        assert last.name == "B"

    async def test_exclude(self, backend):
        """Test exclude filter."""
        await Item.create(name="Keep")
        await Item.create(name="Remove")
        results = await Item.exclude(name="Remove").all()
        assert len(results) == 1
        assert results[0].name == "Keep"

    async def test_order_by(self, backend):
        """Test ordering."""
        await Item.create(name="B")
        await Item.create(name="A")
        await Item.create(name="C")
        asc = await Item.all().order_by("name")
        desc = await Item.all().order_by("-name")
        assert [i.name for i in asc] == ["A", "B", "C"]
        assert [i.name for i in desc] == ["C", "B", "A"]

    async def test_limit_offset(self, backend):
        """Test pagination."""
        for i in range(5):
            await Item.create(name=f"Item{i}")
        page = await Item.all().order_by("name").limit(2).offset(1)
        assert len(page) == 2
        assert page[0].name == "Item1"

    async def test_values(self, backend):
        """Test values returns dicts."""
        await Item.create(name="Test", description="Desc")
        result = await Item.filter(name="Test").values("name", "description")
        assert result == [{"name": "Test", "description": "Desc"}]

    async def test_values_list(self, backend):
        """Test values_list returns tuples."""
        await Item.create(name="Test", description="Desc")
        result = await Item.filter(name="Test").values_list("name", "description")
        assert result == [("Test", "Desc")]

    async def test_distinct(self, backend):
        """Test distinct values."""
        await Item.create(name="Same")
        await Item.create(name="Same")
        await Item.create(name="Different")
        result = await Item.all().distinct().values_list("name", flat=True)
        assert set(result) == {"Same", "Different"}

    async def test_in_bulk(self, backend):
        """Test in_bulk returns dict keyed by field."""
        item1 = await Item.create(name="One")
        item2 = await Item.create(name="Two")
        # Types ignored currently due to https://github.com/tortoise/tortoise-orm/issues/2052
        bulk = await Item.all().in_bulk([item1.id, item2.id], "id")  # type: ignore[arg-type]
        assert bulk[item1.id].name == "One"  # type: ignore[index]
        assert bulk[item2.id].name == "Two"  # type: ignore[index]

    async def test_queryset_update(self, backend):
        """Test bulk update via QuerySet."""
        await Item.create(name="Old1")
        await Item.create(name="Old2")
        await Item.filter(name__startswith="Old").update(description="Updated")
        items = await Item.all()
        assert all(i.description == "Updated" for i in items)

    async def test_queryset_delete(self, backend):
        """Test bulk delete via QuerySet."""
        await Item.create(name="Keep")
        await Item.create(name="Delete1")
        await Item.create(name="Delete2")
        await Item.filter(name__startswith="Delete").delete()
        assert await Item.all().count() == 1

    async def test_refresh_from_db(self, backend):
        """Test refresh_from_db reloads instance."""
        item = await Item.create(name="Original")
        await Item.filter(id=item.id).update(name="Changed")
        assert item.name == "Original"
        await item.refresh_from_db()
        assert item.name == "Changed"

    async def test_earliest_latest(self, backend):
        """Test earliest/latest by field."""
        await Item.create(name="Z")
        await Item.create(name="A")
        earliest = await Item.all().earliest("name")
        latest = await Item.all().latest("name")
        assert earliest is not None
        assert latest is not None
        assert earliest.name == "A"
        assert latest.name == "Z"
