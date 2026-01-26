# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for IntEnumField."""

import uuid
from enum import IntEnum

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class Priority(IntEnum):
    LOW = 1
    HIGH = 2


class IntEnumModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.IntEnumField(Priority)

    class Meta:
        table = "test_intenum"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestIntEnumField:
    async def test_create_read(self, backend):
        obj = await IntEnumModel.create(value=Priority.HIGH)
        fetched = await IntEnumModel.get(id=obj.id)
        assert fetched.value == Priority.HIGH
