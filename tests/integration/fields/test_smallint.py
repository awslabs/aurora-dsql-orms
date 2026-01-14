# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for SmallIntField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class SmallIntModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.SmallIntField()

    class Meta:
        table = "test_smallint"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestSmallIntField:
    async def test_create_read(self, backend):
        obj = await SmallIntModel.create(value=32767)
        fetched = await SmallIntModel.get(id=obj.id)
        assert fetched.value == 32767
