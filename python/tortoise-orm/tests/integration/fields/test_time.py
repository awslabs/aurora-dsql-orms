# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for TimeField."""

import uuid
from datetime import time

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class TimeModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.TimeField()

    class Meta:
        table = "test_time"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestTimeField:
    async def test_create_read(self, backend):
        t = time(14, 30, 0)
        obj = await TimeModel.create(value=t)
        fetched = await TimeModel.get(id=obj.id)
        assert fetched.value.replace(tzinfo=None) == t
