# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for UUIDField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class UUIDModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.UUIDField()

    class Meta:
        table = "test_uuid"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestUUIDField:
    async def test_create_read(self, backend):
        val = uuid.uuid4()
        obj = await UUIDModel.create(value=val)
        fetched = await UUIDModel.get(id=obj.id)
        assert fetched.value == val
