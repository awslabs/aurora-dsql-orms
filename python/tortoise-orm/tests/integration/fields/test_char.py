# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for CharField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class CharModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.CharField(max_length=100)

    class Meta:
        table = "test_char"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestCharField:
    async def test_create_read(self, backend):
        obj = await CharModel.create(value="hello")
        fetched = await CharModel.get(id=obj.id)
        assert fetched.value == "hello"
