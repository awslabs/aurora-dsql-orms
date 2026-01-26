# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for TimeDeltaField."""

import uuid
from datetime import timedelta

import pytest
from tortoise import fields
from tortoise.models import Model

from tests.conftest import BACKENDS


class TimeDeltaModel(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    value = fields.TimeDeltaField()

    class Meta:
        table = "test_timedelta"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestTimeDeltaField:
    async def test_create_read(self, backend):
        td = timedelta(days=1, hours=2)
        obj = await TimeDeltaModel.create(value=td)
        fetched = await TimeDeltaModel.get(id=obj.id)
        assert fetched.value == td
