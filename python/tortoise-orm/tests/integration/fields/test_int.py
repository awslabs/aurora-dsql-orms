# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for IntField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class IntModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.IntField()

    class Meta:
        table = "test_int"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestIntField:
    async def test_create_read(self, backend):
        obj = await IntModel.create(value=42)
        fetched = await IntModel.get(id=obj.id)
        assert fetched.value == 42
