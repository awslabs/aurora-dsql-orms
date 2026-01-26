# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import os
import re

import pytest
from dotenv import load_dotenv
from tortoise import Tortoise
from tortoise.backends.base.executor import EXECUTOR_CACHE

load_dotenv()

CLUSTER_ENDPOINT = os.environ.get("CLUSTER_ENDPOINT")
CLUSTER_USER = os.environ.get("CLUSTER_USER", "admin")

match = re.match(r"^([a-z0-9]+)\.dsql(?:-[^.]+)?\.([a-z0-9-]+)\.on\.aws$", CLUSTER_ENDPOINT or "")
if not match:
    raise ValueError(f"Invalid CLUSTER_ENDPOINT format: {CLUSTER_ENDPOINT}")
CLUSTER_ID, REGION = match.groups()

OCC_CLEANUP_RETRIES = 5


@pytest.fixture
async def backend(request):
    # Clear cached queries to avoid cross-backend pollution.
    EXECUTOR_CACHE.clear()

    backend_name = request.param

    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend_name}",
                    "credentials": {"host": CLUSTER_ENDPOINT, "user": CLUSTER_USER},
                }
            },
            "apps": {
                "models": {"models": [request.module.__name__], "default_connection": "default"}
            },
        }
    )
    try:
        yield backend_name
    finally:
        await Tortoise.close_connections()


@pytest.fixture(autouse=True)
async def schemas(request, backend):
    if request.node.get_closest_marker("use_schemas"):
        await Tortoise.generate_schemas()


async def assert_connection_works():
    """Validate that a connection can execute a simple query."""
    conn = Tortoise.get_connection("default")
    result = await conn.execute_query("SELECT 1 as value")
    assert result[1][0]["value"] == 1


@pytest.fixture(autouse=True)
async def cleanup_test_tables(backend):
    """Drop all test tables with OCC retries to ensure a clean state after each test."""
    yield

    conn = Tortoise.get_connection("default")
    errors = []
    for attempt in range(OCC_CLEANUP_RETRIES):
        try:
            result = await conn.execute_query(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
            for row in result[1]:
                await conn.execute_query(f'DROP TABLE IF EXISTS "{row["table_name"]}" CASCADE')
            break
        except Exception as e:
            errors.append(e)
            if "OC00" in str(e):
                await asyncio.sleep(0.1 * (attempt + 1))
                continue
            raise
    else:
        raise Exception(f"cleanup failed after retries: {errors}")

    await Tortoise.close_connections()
