# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for TextField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class TextModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.TextField()

    class Meta:
        table = "test_text"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestTextField:
    async def test_create_read(self, backend):
        obj = await TextModel.create(value="x" * 1000)
        fetched = await TextModel.get(id=obj.id)
        assert fetched.value == "x" * 1000
