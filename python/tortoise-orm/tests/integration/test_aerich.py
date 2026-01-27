# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import shutil
import tempfile
import uuid
from pathlib import Path
from textwrap import dedent

import pytest
from aerich import Command
from aerich.migrate import Migrate
from aerich.models import Aerich
from tortoise import Tortoise, connections
from tortoise.backends.base.executor import EXECUTOR_CACHE

from tests.conftest import BACKENDS

from .conftest import CLUSTER_ENDPOINT, CLUSTER_USER

AERICH_MODELS = "tests.integration.aerich_models.basic"
ADD_COLUMN_V1 = "tests.integration.aerich_models.add_column_v1"
ADD_COLUMN_V2 = "tests.integration.aerich_models.add_column_v2"
ADD_MODEL_V1 = "tests.integration.aerich_models.add_model_v1"
ADD_MODEL_V2 = "tests.integration.aerich_models.add_model_v2"
ADD_MODEL_V3 = "tests.integration.aerich_models.add_model_v3"
MULTI_MODEL_V1 = "tests.integration.aerich_models.multi_model_v1"
MULTI_MODEL_V2 = "tests.integration.aerich_models.multi_model_v2"


def reset_orm():
    """Reset all ORM and migration state for test isolation."""
    EXECUTOR_CACHE.clear()

    connections._clear_storage()
    if connections._db_config is not None:
        connections.db_config.clear()

    Tortoise.apps = {}
    Tortoise._inited = False

    Migrate.upgrade_operators = []
    Migrate.downgrade_operators = []
    Migrate.migrate_location = None  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def reset_orm_state():
    """Reset ORM state before each test."""
    reset_orm()


@pytest.fixture
def migration_dir():
    """Provide a temporary directory for generated migration files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir) / "migrations"
    shutil.rmtree(temp_dir, ignore_errors=True)


def make_config(models: list[str], backend: str) -> dict:
    """Create a Tortoise config with the given models."""
    return {
        "connections": {
            "default": {
                "engine": f"aurora_dsql_tortoise.{backend}",
                "credentials": {"host": CLUSTER_ENDPOINT, "user": CLUSTER_USER},
            }
        },
        "apps": {
            "models": {
                "models": models + ["aerich.models", "aurora_dsql_tortoise.aerich"],
                "default_connection": "default",
            }
        },
    }


async def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the public schema."""
    result = await conn.execute_query(
        "SELECT 1 FROM information_schema.tables "
        f"WHERE table_schema = 'public' AND table_name = '{table_name}'"
    )
    return len(result[1]) > 0


async def get_table_columns(conn, table_name: str) -> set[str]:
    """Get column names for a table."""
    result = await conn.execute_query(
        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
    )
    return {row["column_name"] for row in result[1]}


async def make_command(models: list[str], migration_dir: Path, backend: str) -> Command:
    """Create and initialize an aerich Command."""
    config = make_config(models, backend)
    command = Command(tortoise_config=config, app="models", location=str(migration_dir))
    await command.init()
    return command


async def migrate_to(models: list[str], migration_dir: Path, backend: str, name: str) -> Command:
    """Switch models and apply a migration."""
    await Tortoise.close_connections()
    reset_orm()
    command = await make_command(models, migration_dir, backend)
    migration_name = await command.migrate(name, no_input=True)
    assert migration_name is not None, "Migration should be generated"
    await command.upgrade()
    return command


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_migration_workflow(migration_dir, backend):
    command = await make_command([AERICH_MODELS], migration_dir, backend)
    await command.init_db(safe=True)

    # Verify migration files were created.
    assert list(migration_dir.rglob("*.py")), "Migration files should be created"

    # Verify tables exist in database.
    conn = Tortoise.get_connection("default")
    assert await table_exists(conn, "aerich_test_model"), "aerich_test_model table should exist"
    assert await table_exists(conn, "aerich"), "aerich table should exist"


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_upgraded_table_is_valid(migration_dir, backend):
    command = await make_command([AERICH_MODELS], migration_dir, backend)
    await command.init_db(safe=True)

    # Verify we can insert data into the created table.
    conn = Tortoise.get_connection("default")
    test_id = str(uuid.uuid4())
    await conn.execute_query(
        f"INSERT INTO aerich_test_model (id, name) VALUES ('{test_id}', 'test')"
    )

    result = await conn.execute_query(f"SELECT name FROM aerich_test_model WHERE id = '{test_id}'")
    assert result[1][0]["name"] == "test"


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_add_column_migration(migration_dir, backend):
    """Test generating and applying an incremental migration that adds a field."""

    # Initial migration with V1.
    command = await make_command([ADD_COLUMN_V1], migration_dir, backend)
    await command.init_db(safe=True)

    # Verify V1 columns.
    conn = Tortoise.get_connection("default")
    columns = await get_table_columns(conn, "incremental_test_model")
    assert "name" in columns
    assert "description" not in columns

    # Switch to V2 model and apply migration.
    await migrate_to([ADD_COLUMN_V2], migration_dir, backend, "add_description")

    # Verify new column exists.
    conn = Tortoise.get_connection("default")
    columns = await get_table_columns(conn, "incremental_test_model")
    assert "description" in columns

    # Verify column works.
    test_id = str(uuid.uuid4())
    await conn.execute_query(
        f"INSERT INTO incremental_test_model (id, name, description) "
        f"VALUES ('{test_id}', 'test', 'test desc')"
    )
    result = await conn.execute_query(
        f"SELECT description FROM incremental_test_model WHERE id = '{test_id}'"
    )
    assert result[1][0]["description"] == "test desc"

    # Note: Downgrade not tested here because DSQL doesn't support ALTER TABLE DROP COLUMN.
    # See other tests for downgrade testing.


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_add_model_and_downgrade_last(migration_dir, backend):
    """Test downgrading to the previous migration version, using a new model."""

    # Initial migration with V1.
    command = await make_command([ADD_MODEL_V1], migration_dir, backend)
    await command.init_db(safe=True)

    # Verify V1 state.
    conn = Tortoise.get_connection("default")
    assert await table_exists(conn, "existing_model")
    assert not await table_exists(conn, "second_model")

    # Switch to V2 model and apply migration.
    command = await migrate_to([ADD_MODEL_V2], migration_dir, backend, "add_second_model")

    # Verify new table exists and works.
    conn = Tortoise.get_connection("default")
    assert await table_exists(conn, "second_model")
    result = await conn.execute_query(
        "INSERT INTO second_model (id, title) VALUES (gen_random_uuid(), 'test title') "
        "RETURNING id, title"
    )
    assert result[1][0]["title"] == "test title"

    # Downgrade and verify table is removed.
    await command.downgrade(version=-1, delete=False)
    conn = Tortoise.get_connection("default")
    assert not await table_exists(conn, "second_model"), (
        "second_model should be dropped after downgrade"
    )
    assert await table_exists(conn, "existing_model"), "existing_model should still exist"


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_add_model_and_downgrade_to_version(migration_dir, backend):
    """Test downgrading to a specific version number, using a new model."""

    # Initial migration with V1.
    command = await make_command([ADD_MODEL_V1], migration_dir, backend)
    await command.init_db(safe=True)

    # Switch to V2 model and apply migration.
    await migrate_to([ADD_MODEL_V2], migration_dir, backend, "add_second_model")

    # Switch to V3 model and apply migration.
    command = await migrate_to([ADD_MODEL_V3], migration_dir, backend, "add_third_model")

    # Verify all tables exist.
    conn = Tortoise.get_connection("default")
    assert await table_exists(conn, "existing_model")
    assert await table_exists(conn, "second_model")
    assert await table_exists(conn, "third_model")

    # Downgrade to V1 (should remove V2 and V3)
    await command.downgrade(version=1, delete=False)

    conn = Tortoise.get_connection("default")
    assert await table_exists(conn, "existing_model"), "existing_model should remain"
    assert not await table_exists(conn, "second_model"), "second_model should be dropped"
    assert not await table_exists(conn, "third_model"), "third_model should be dropped"


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_downgrade_version_ordering(migration_dir, backend):
    """Test downgrading with double-digit versions uses numeric comparison.

    String comparison would fail lexicographically since '10_...' < '2_...'
    """
    # V1: Initial migration.
    command = await make_command([ADD_MODEL_V1], migration_dir, backend)
    await command.init_db(safe=True)

    # V2-V11: Create fake migrations to get a double-digit version (10), since
    # the migration count is 0-based.
    models_dir = Path(Migrate.migrate_location)
    migration_content = dedent("""
        async def upgrade(db):
            return ''

        async def downgrade(db):
            return 'SELECT 1'
    """).lstrip()

    for i in range(1, 11):
        filename = f"{i}_fake_migration.py"
        (models_dir / filename).write_text(migration_content)
        await Aerich.create(version=filename, app="models", content={})

    # V1 + V2-V11 = 11 versions total (indices 0-10).
    all_versions = await Aerich.filter(app="models").all()
    assert len(all_versions) == 11

    # Downgrade to V3: undoes V4-V11 (indices 3-10 = 8 versions).
    # We choose V3 so that indices 0-2 remain. If index 10 were incorrectly
    # included due to string sorting, it would appear before index 2.
    result = await command.downgrade(version=3, delete=False, fake=True)
    assert len(result) == 8, f"Expected 8 downgrades, got {len(result)}: {result}"

    # V1-V3 (indices 0-2) should remain.
    remaining = await Aerich.filter(app="models").all()
    assert len(remaining) == 3
    remaining_indices = sorted(int(v.version.split("_")[0]) for v in remaining)
    assert remaining_indices == [0, 1, 2]


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_heads(migration_dir, backend):
    """Test heads command shows unapplied migrations."""

    # Initial migration with V1.
    command = await make_command([ADD_MODEL_V1], migration_dir, backend)
    await command.init_db(safe=True)

    # Generate migration for V2 but don't apply it.
    await Tortoise.close_connections()
    reset_orm()
    command = await make_command([ADD_MODEL_V2], migration_dir, backend)
    await command.migrate("add_second_model", no_input=True)

    # heads should show the unapplied migration.
    heads = await command.heads()
    assert len(heads) == 1
    assert "add_second_model" in heads[0]

    # After upgrade, heads should be empty.
    await command.upgrade()
    heads = await command.heads()
    assert len(heads) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_history(migration_dir, backend):
    """Test history lists all migration files."""

    # Initial migration with V1.
    command = await make_command([ADD_MODEL_V1], migration_dir, backend)
    await command.init_db(safe=True)

    # Should have 1 migration (V1).
    history = await command.history()
    assert len(history) == 1

    # Add V2 migration.
    command = await migrate_to([ADD_MODEL_V2], migration_dir, backend, "add_second_model")

    # Should have 2 migrations (V1, V2).
    history = await command.history()
    assert len(history) == 2
    assert "add_second_model" in history[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_inspectdb(migration_dir, backend):
    """Test inspectdb generates model code from existing tables."""

    # Initial migration with V1.
    command = await make_command([ADD_MODEL_V1], migration_dir, backend)
    await command.init_db(safe=True)

    output = await command.inspectdb(tables=["existing_model"])

    assert "class ExistingModel" in output
    assert "fields.UUIDField(primary_key=True)" in output
    assert "fields.CharField(max_length=100)" in output


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_ordering_by_version_not_uuid(migration_dir, backend):
    """Test that Aerich records are ordered by version, not UUID."""

    # Initial migration with V1.
    command = await make_command([ADD_MODEL_V1], migration_dir, backend)
    await command.init_db(safe=True)

    # Insert records with fake UUIDs that sort opposite to version order.
    await Aerich.create(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        version="1_newer.py",
        app="models",
        content={},
    )
    await Aerich.create(
        id=uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        version="0_older.py",
        app="models",
        content={},
    )

    # first() should return "1_older" (highest version), not "fff..." (highest UUID).
    first = await Aerich.all().first()
    assert first is not None and first.version == "1_newer.py", (
        f"Should order by version not UUID, got: {first}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_multi_model_migration(migration_dir, backend):
    """Test migration that adds multiple models at once (triggers multi-DDL splitting)."""

    # Initial migration with V1.
    command = await make_command([MULTI_MODEL_V1], migration_dir, backend)
    await command.init_db(safe=True)

    conn = Tortoise.get_connection("default")
    assert await table_exists(conn, "multi_base_model")
    assert not await table_exists(conn, "multi_model_a")
    assert not await table_exists(conn, "multi_model_b")

    # Switch to V2 model and apply migration. Should add 2 models.
    command = await migrate_to([MULTI_MODEL_V2], migration_dir, backend, "add_two_models")

    conn = Tortoise.get_connection("default")
    assert await table_exists(conn, "multi_model_a"), "multi_model_a should be created"
    assert await table_exists(conn, "multi_model_b"), "multi_model_b should be created"

    # Downgrade to V1 model. Should remove 2 models.
    await command.downgrade(version=-1, delete=False)

    conn = Tortoise.get_connection("default")
    assert not await table_exists(conn, "multi_model_a"), "multi_model_a should be dropped"
    assert not await table_exists(conn, "multi_model_b"), "multi_model_b should be dropped"
    assert await table_exists(conn, "multi_base_model"), "multi_base_model should remain"


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_aerich_init_with_multi_statement_pre_sql(migration_dir, backend):
    """Test init_db with pre_sql containing multiple statements (triggers multi-DDL splitting)."""
    pre_sql = """
        CREATE TABLE pre_sql_table_a (id UUID PRIMARY KEY, val TEXT);
        CREATE TABLE pre_sql_table_b (id UUID PRIMARY KEY, num INT);
    """
    command = await make_command([AERICH_MODELS], migration_dir, backend)
    await command.init_db(safe=True, pre_sql=pre_sql)

    conn = Tortoise.get_connection("default")
    assert await table_exists(conn, "pre_sql_table_a"), "pre_sql_table_a should be created"
    assert await table_exists(conn, "pre_sql_table_b"), "pre_sql_table_b should be created"
