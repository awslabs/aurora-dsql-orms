# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for DatetimeField."""

import uuid
from datetime import datetime

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class DatetimeModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.DatetimeField()

    class Meta:
        table = "test_datetime"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestDatetimeField:
    async def test_create_read(self, backend):
        dt = datetime(2025, 6, 15, 10, 30, 0)
        obj = await DatetimeModel.create(value=dt)
        fetched = await DatetimeModel.get(id=obj.id)
        assert fetched.value.replace(tzinfo=None) == dt
