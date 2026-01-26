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
    content = aerich.models.Aerich._meta.fields_map['content']

    assert type(pk).__name__ == 'UUIDField', f'Expected UUIDField, got {type(pk).__name__}'
    assert content.SQL_TYPE == 'TEXT', f'Expected TEXT, got {content.SQL_TYPE}'
    assert 'RUN_IN_TRANSACTION = False' in aerich.migrate.MIGRATE_TEMPLATE

    await Tortoise.close_connections()
    print('OK')

asyncio.run(test())
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "OK" in result.stdout
