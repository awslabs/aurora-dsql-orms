# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for ForeignKeyField."""

import uuid

import pytest
from tortoise import fields
from tortoise.fields.relational import ReverseRelation
from tortoise.models import Model

from tests.conftest import BACKENDS


class FKParent(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    children: ReverseRelation["FKChild"]

    class Meta:
        table = "test_fk_parent"


class FKChild(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    parent = fields.ForeignKeyField("models.FKParent", related_name="children")

    class Meta:
        table = "test_fk_child"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestForeignKeyField:
    async def test_create_read(self, backend):
        parent = await FKParent.create()
        child = await FKChild.create(parent=parent)
        fetched = await FKChild.get(id=child.id).prefetch_related("parent")
        assert fetched.parent.id == parent.id

    async def test_reverse_relation(self, backend):
        parent = await FKParent.create()
        child = await FKChild.create(parent=parent)
        fetched = await FKParent.get(id=parent.id).prefetch_related("children")
        assert len(fetched.children) == 1
        assert fetched.children[0].id == child.id
