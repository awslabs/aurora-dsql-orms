# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid
from pathlib import Path

import aerich.migrate
import aerich.models
from aerich import Command
from aerich.coder import decoder, encoder
from aerich.ddl.postgres import PostgresDDL
from aerich.exceptions import DowngradeError
from aerich.migrate import Migrate
from aerich.models import Aerich
from aerich.utils import (
    decompress_dict,
    file_module_info,
    get_app_connection,
    get_models_describe,
    import_py_file,
    import_py_module,
    py_module_path,
)
from pypika_tortoise.enums import Order
from tortoise import Tortoise, fields

from aurora_dsql_tortoise.common.config import split_sql
from aurora_dsql_tortoise.common.schema_generator import AuroraDSQLBaseSchemaGenerator

# --- Aerich model patches ---

# Patch Aerich internal model ID field to use UUID.
_uuid_field = fields.UUIDField(primary_key=True, default=uuid.uuid4)
_uuid_field.model = aerich.models.Aerich
_uuid_field.model_field_name = "id"
aerich.models.Aerich._meta.fields_map["id"] = _uuid_field
aerich.models.Aerich._meta.pk = _uuid_field


# Patch Aerich internal model JSON field to use TEXT.
_json_field = fields.JSONField(encoder=encoder, decoder=decoder)
_json_field.model = aerich.models.Aerich
_json_field.model_field_name = "content"
_json_field.SQL_TYPE = "TEXT"
_json_field._db_postgres = type("_", (), {"SQL_TYPE": "TEXT"})  # type: ignore[method-assign]
aerich.models.Aerich._meta.fields_map["content"] = _json_field

# Patch ordering to use version instead of id (UUIDs don't sort chronologically).
aerich.models.Aerich._meta._default_ordering = (("version", Order.desc),)


# --- Migration behavior patches ---

# Patch migration template to disable the wrapping transaction. Transactions in
# Aurora DSQL can contain only one DDL statement.
aerich.migrate.MIGRATE_TEMPLATE = aerich.migrate.MIGRATE_TEMPLATE.replace(
    "RUN_IN_TRANSACTION = True", "RUN_IN_TRANSACTION = False"
)

# Use DSQL-compatible schema generator for DDL generation.
PostgresDDL.schema_generator_cls = AuroraDSQLBaseSchemaGenerator


# --- Patched methods ---


async def _execute_ddl(conn, sql: str) -> None:
    """Execute DDL statements one at a time; transactions in Aurora DSQL can
    contain only one DDL statement."""
    for stmt in split_sql(sql):
        await conn.execute_script(stmt)


async def _patched_upgrade(self, conn, version_file, fake=False, version_module=None):
    """Upgrade with DSQL-compatible DDL execution."""
    # This code is based on Aerich
    # Modifications: Copyright (c) Amazon.com, Inc. or its affiliates.
    # License to Modifications: Apache 2.0
    # Source: https://github.com/tortoise/aerich/blob/19f8e042b2f2ff621b08e79f1123f1d8bbf2a109/aerich/__init__.py#L103
    if version_module is not None:
        m = import_py_module(version_module)
    else:
        m = import_py_file(Path(Migrate.migrate_location, version_file))

    upgrade_fn = m.upgrade
    if not fake:
        # Main change is here, to execute within DSQL requirements.
        await _execute_ddl(conn, await upgrade_fn(conn))

    model_state_str = getattr(m, "MODELS_STATE", None)
    models_state = (
        decompress_dict(model_state_str) if model_state_str else get_models_describe(self.app)
    )
    await Aerich.create(version=version_file, app=self.app, content=models_state)


async def _patched_downgrade(self: Command, version: int, delete: bool, fake: bool = False):
    """Downgrade with DSQL-compatible DDL execution."""
    # This code is based on Aerich
    # Modifications: Copyright (c) Amazon.com, Inc. or its affiliates.
    # License to Modifications: Apache 2.0
    # Source: https://github.com/tortoise/aerich/blob/19f8e042b2f2ff621b08e79f1123f1d8bbf2a109/aerich/__init__.py#L145
    ret: list[str] = []

    if version == -1:
        specified_version = await Migrate.get_last_version()
    else:
        specified_version = await Aerich.filter(
            app=self.app, version__startswith=f"{version}_"
        ).first()

    if not specified_version:
        raise DowngradeError("No specified version found")

    if version == -1:
        versions = [specified_version]
    else:
        # This differs from upstream, as we need to filter on the version given
        # UUIDs do not have a predictable sort order.
        all_versions = await Aerich.filter(app=self.app)
        versions = [v for v in all_versions if int(v.version.split("_")[0]) >= version]

    conn = get_app_connection(self.tortoise_config, self.app)

    # This differs from upstream, a wrapping transaction was removed, so we rely
    # on DSQL's OCC model.
    for version_obj in versions:
        file = version_obj.version
        module_info = file_module_info(Migrate.migrate_location, Path(file).stem)
        m = import_py_module(module_info)
        downgrade = m.downgrade
        downgrade_sql = await downgrade(conn)

        if not downgrade_sql.strip():
            raise DowngradeError("No downgrade items found")

        if not fake:
            # This differs from upstream, to execute within DSQL requirements.
            await _execute_ddl(conn, downgrade_sql)

        await version_obj.delete()

        if delete:
            py_module_path(module_info).unlink()

        ret.append(file)

    return ret


# Store original method for chaining.
_original_do_init = Command._do_init


async def _patched_do_init(self, safe: bool, pre_sql: str | None = None, offline: bool = False):
    """init_db with DSQL-compatible pre_sql execution."""
    if pre_sql:
        await Tortoise.init(config=self.tortoise_config)
        conn = get_app_connection(self.tortoise_config, self.app)
        await _execute_ddl(conn, pre_sql)
        # Call original with pre_sql=None since we executed it already.
        await _original_do_init(self, safe, pre_sql=None, offline=offline)
    else:
        await _original_do_init(self, safe, pre_sql, offline)


Command._upgrade = _patched_upgrade  # type: ignore[method-assign]
Command._do_init = _patched_do_init  # type: ignore[method-assign]
Command.downgrade = _patched_downgrade  # type: ignore[method-assign]
