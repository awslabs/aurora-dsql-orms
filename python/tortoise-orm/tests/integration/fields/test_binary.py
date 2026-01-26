# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for BinaryField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class BinaryModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.BinaryField()

    class Meta:
        table = "test_binary"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestBinaryField:
    async def test_create_read(self, backend):
        obj = await BinaryModel.create(value=b"\xde\xad\xbe\xef")
        fetched = await BinaryModel.get(id=obj.id)
        assert fetched.value == b"\xde\xad\xbe\xef"
