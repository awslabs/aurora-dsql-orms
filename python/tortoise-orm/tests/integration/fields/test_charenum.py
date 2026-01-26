# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for CharEnumField."""

import uuid
from enum import Enum

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CharEnumModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.CharEnumField(Status)

    class Meta:
        table = "test_charenum"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestCharEnumField:
    async def test_create_read(self, backend):
        obj = await CharEnumModel.create(value=Status.ACTIVE)
        fetched = await CharEnumModel.get(id=obj.id)
        assert fetched.value == Status.ACTIVE
