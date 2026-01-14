# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for BooleanField."""

import uuid

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class BoolModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.BooleanField()

    class Meta:
        table = "test_bool"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestBooleanField:
    async def test_create_read(self, backend):
        obj = await BoolModel.create(value=True)
        fetched = await BoolModel.get(id=obj.id)
        assert fetched.value is True
