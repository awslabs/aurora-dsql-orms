# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for BigIntField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class BigIntModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.BigIntField()

    class Meta:
        table = "test_bigint"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestBigIntField:
    async def test_create_read(self, backend):
        obj = await BigIntModel.create(value=9223372036854775807)
        fetched = await BigIntModel.get(id=obj.id)
        assert fetched.value == 9223372036854775807
