# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid

import pytest
from tortoise import Tortoise, fields
from tortoise.models import Model
from tortoise.transactions import in_transaction

from tests.conftest import BACKENDS


class TxItem(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "test_tx_item"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestTransactions:
    async def test_commit(self, backend):
        """Test transaction commits on success."""
        async with in_transaction():
            await TxItem.create(name="Committed")
        assert await TxItem.filter(name="Committed").exists()

    async def test_rollback_on_exception(self, backend):
        """Test transaction rolls back on exception."""
        try:
            async with in_transaction():
                await TxItem.create(name="RolledBack")
                raise ValueError("Force rollback")
        except ValueError:
            pass
        assert not await TxItem.filter(name="RolledBack").exists()

    async def test_ddl_in_transaction(self, backend):
        """Test DDL operations in transaction context."""
        conn = Tortoise.get_connection("default")
        async with in_transaction():
            await conn.execute_script("CREATE TABLE test_ddl_tx (id UUID PRIMARY KEY, val TEXT)")
        result = await conn.execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_name = 'test_ddl_tx'"
        )
        assert len(result[1]) == 1
