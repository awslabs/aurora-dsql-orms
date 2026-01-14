# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for DateField."""

import uuid
from datetime import date

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class DateModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.DateField()

    class Meta:
        table = "test_date"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestDateField:
    async def test_create_read(self, backend):
        obj = await DateModel.create(value=date(2025, 6, 15))
        fetched = await DateModel.get(id=obj.id)
        assert fetched.value == date(2025, 6, 15)
