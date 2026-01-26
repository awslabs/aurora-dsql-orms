# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for DecimalField."""

import uuid
from decimal import Decimal

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class DecimalModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        table = "test_decimal"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestDecimalField:
    async def test_create_read(self, backend):
        obj = await DecimalModel.create(value=Decimal("123.45"))
        fetched = await DecimalModel.get(id=obj.id)
        assert fetched.value == Decimal("123.45")
