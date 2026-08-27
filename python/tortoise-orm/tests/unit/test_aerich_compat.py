# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
These tests run in isolated subprocesses because they test module imports and
patching. The module patches aerich for the entire process, so tests must
start with a fresh Python interpreter to avoid cross-contamination from other
tests.
"""

import subprocess
import sys


def test_aerich_without_patches_uses_default_fields():
    """Verify aerich uses IntField PK and JSONB when module is not in models list."""
    code = """
import asyncio
from tortoise import Tortoise

async def test():
    await Tortoise.init(config={
        'connections': {'default': 'sqlite://:memory:'},
        'apps': {
            'models': {
                'models': ['aerich.models'],
                'default_connection': 'default',
            }
        }
    })

    import aerich.models
    import aerich.migrate

    pk = aerich.models.Aerich._meta.pk
    assert type(pk).__name__ == 'IntField', f'Expected IntField, got {type(pk).__name__}'
    assert 'RUN_IN_TRANSACTION = True' in aerich.migrate.MIGRATE_TEMPLATE

    await Tortoise.close_connections()
    print('OK')

asyncio.run(test())
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "OK" in result.stdout


def test_aerich_with_module_in_models_applies_patches():
    """Verify adding aerich module to models list applies DSQL patches."""
    code = """
import asyncio
from tortoise import Tortoise

async def test():
    await Tortoise.init(config={
        'connections': {'default': 'sqlite://:memory:'},
        'apps': {
            'models': {
                'models': ['aerich.models', 'aurora_dsql_tortoise.aerich'],
                'default_connection': 'default',
            }
        }
    })

    import aerich.models
    import aerich.migrate

    pk = aerich.models.Aerich._meta.pk

    assert type(pk).__name__ == 'UUIDField', f'Expected UUIDField, got {type(pk).__name__}'
    assert 'RUN_IN_TRANSACTION = False' in aerich.migrate.MIGRATE_TEMPLATE

    await Tortoise.close_connections()
    print('OK')

asyncio.run(test())
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "OK" in result.stdout


def test_aerich_foreign_key_migrations_use_two_phase_validation():
    """Verify Aerich emits and awaits DSQL-compatible incremental FKs."""
    code = """
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from tortoise import Tortoise

async def test():
    await Tortoise.init(config={
        'connections': {'default': 'sqlite://:memory:'},
        'apps': {
            'models': {
                'models': ['aerich.models', 'aurora_dsql_tortoise.aerich'],
                'default_connection': 'default',
            }
        }
    })

    from aerich.ddl.postgres import PostgresDDL
    from aurora_dsql_tortoise.aerich.patch import _execute_ddl

    ddl = PostgresDDL(MagicMock())
    ddl._generate_fk_name = MagicMock(return_value='child_parent_fk')
    model = SimpleNamespace(_meta=SimpleNamespace(db_table='child'))
    field = {'raw_field': 'parent_id', 'on_delete': 'RESTRICT'}
    reference = {
        'table': 'parent',
        'pk_field': {'db_column': 'id'},
    }
    sql = ddl.add_fk(model, field, reference)
    assert 'NOT VALID' in sql
    assert (
        'ALTER TABLE ASYNC "child" VALIDATE CONSTRAINT "child_parent_fk"'
        in sql
    )
    drop_sql = ddl.drop_fk(model, field, reference)
    assert (
        drop_sql
        == 'ALTER TABLE "child" DROP CONSTRAINT IF EXISTS "child_parent_fk"'
    )

    for placeholder in ('$1', '%s'):
        conn = MagicMock()
        conn.parameter_placeholder = placeholder
        conn.execute_script = AsyncMock()
        conn.execute_query = AsyncMock(
            side_effect=[
                (1, [{'job_id': 'job-123'}]),
                (1, [{'succeeded': True}]),
            ]
        )
        await _execute_ddl(conn, sql)
        assert conn.execute_script.await_count == 1
        assert conn.execute_query.await_count == 2
        wait_call = conn.execute_query.await_args_list[1]
        assert f'sys.wait_for_job({placeholder})' in wait_call.args[0]

    conn = MagicMock()
    conn.execute_script = AsyncMock()
    conn.execute_query = AsyncMock()
    await _execute_ddl(conn, drop_sql)
    conn.execute_script.assert_awaited_once_with(drop_sql)
    conn.execute_query.assert_not_awaited()

    await Tortoise.close_connections()
    print('OK')

asyncio.run(test())
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "OK" in result.stdout
