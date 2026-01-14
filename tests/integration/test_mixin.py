# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid

import pytest
from tortoise import fields

from aurora_dsql_tortoise import DSQLModel
from tests.conftest import BACKENDS


class MixinItem(DSQLModel):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100)
    description = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "test_mixin_item"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestDSQLModel:
    async def test_update_or_create(self, backend):
        """Test update_or_create works with mixin."""
        item1, created1 = await MixinItem.update_or_create(
            name="Target", defaults={"description": "V1"}
        )
        assert created1
        item2, created2 = await MixinItem.update_or_create(
            name="Target", defaults={"description": "V2"}
        )
        assert not created2
        assert item2.description == "V2"
