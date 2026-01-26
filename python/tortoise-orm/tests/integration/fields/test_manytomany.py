# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for ManyToManyField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class M2MModelA(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    bs = fields.ManyToManyField("models.M2MModelB", related_name="as_")

    class Meta:
        table = "test_m2m_a"


class M2MModelB(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)

    class Meta:
        table = "test_m2m_b"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestManyToManyField:
    async def test_create_read(self, backend):
        a = await M2MModelA.create()
        b = await M2MModelB.create()
        await a.bs.add(b)
        fetched = await M2MModelA.get(id=a.id).prefetch_related("bs")
        assert len(fetched.bs) == 1
        assert fetched.bs[0].id == b.id
