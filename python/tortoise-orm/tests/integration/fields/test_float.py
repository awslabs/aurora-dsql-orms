# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for FloatField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class FloatModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.FloatField()

    class Meta:
        table = "test_float"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestFloatField:
    async def test_create_read(self, backend):
        obj = await FloatModel.create(value=3.14159)
        fetched = await FloatModel.get(id=obj.id)
        assert abs(fetched.value - 3.14159) < 0.00001
