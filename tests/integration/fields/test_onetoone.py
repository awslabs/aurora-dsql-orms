# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for OneToOneField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class O2OModelA(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)

    class Meta:
        table = "test_o2o_a"


class O2OModelB(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    a = fields.OneToOneField("models.O2OModelA", related_name="b")

    class Meta:
        table = "test_o2o_b"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestOneToOneField:
    async def test_create_read(self, backend):
        a = await O2OModelA.create()
        b = await O2OModelB.create(a=a)
        fetched = await O2OModelB.get(id=b.id).prefetch_related("a")
        assert fetched.a.id == a.id
