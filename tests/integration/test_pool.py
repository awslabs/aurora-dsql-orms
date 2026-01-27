# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging

import pytest
from tortoise import Tortoise

from tests.conftest import BACKENDS

from .conftest import CLUSTER_ENDPOINT, CLUSTER_USER, assert_connection_works

logger = logging.getLogger(__name__)


async def get_session_id(connection_name: str = "default") -> str:
    """Get unique session identifier for the current connection."""
    conn = Tortoise.get_connection(connection_name)
    result = await conn.execute_query("SELECT sys.current_session_id() as session_id")
    return result[1][0]["session_id"]


async def wait_for_expiry(expiry: int):
    """Wait long enough for a token duration to expire."""
    wait_time = 2 * expiry
    logger.info(f"Waiting {wait_time}s to exceed expiry time...")
    await asyncio.sleep(wait_time)


async def get_session_id_with_delay(connection_name: str = "default") -> str:
    """Get session ID after a brief sleep to encourage concurrent execution."""
    conn = Tortoise.get_connection(connection_name)
    result = await conn.execute_query(
        "SELECT sys.current_session_id() as session_id FROM pg_sleep(2)"
    )
    return result[1][0]["session_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_pool_size_config_applied(backend: str):
    """Test that minsize/maxsize pool config is correctly applied."""
    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend}",
                    "credentials": {
                        "host": CLUSTER_ENDPOINT,
                        "user": CLUSTER_USER,
                        "minsize": 2,
                        "maxsize": 3,
                    },
                }
            },
            "apps": {},
        }
    )
    await assert_connection_works()

    conn = Tortoise.get_connection("default")
    pool_min = conn._pool.min_size if backend == "psycopg" else conn._pool._minsize
    pool_max = conn._pool.max_size if backend == "psycopg" else conn._pool._maxsize
    assert pool_min == 2
    assert pool_max == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_established_connection_usable_after_token_expiry(backend: str):
    """Test that an established connection remains usable after token would have expired."""
    token_duration_secs = 1

    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend}",
                    "credentials": {
                        "host": CLUSTER_ENDPOINT,
                        "user": CLUSTER_USER,
                        "token_duration_secs": token_duration_secs,
                        "minsize": 1,
                        "maxsize": 1,
                    },
                },
            },
            "apps": {},
        }
    )

    session_id_before = await get_session_id()
    await wait_for_expiry(token_duration_secs)
    session_id_after = await get_session_id()

    assert session_id_before == session_id_after, (
        "Established connection should remain usable after token expiry"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_connection_recycled_after_pool_lifetime_expiry(backend: str):
    """Test that connection is recycled when pool lifetime expires, requiring new token."""
    connection_lifetime_secs = 1

    # psycopg uses max_lifetime, asyncpg uses max_inactive_connection_lifetime
    pool_config = (
        {"max_lifetime": connection_lifetime_secs}
        if backend == "psycopg"
        else {"max_inactive_connection_lifetime": connection_lifetime_secs}
    )

    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend}",
                    "credentials": {
                        "host": CLUSTER_ENDPOINT,
                        "user": CLUSTER_USER,
                        **pool_config,
                    },
                    "minsize": 1,
                    "maxsize": 1,
                }
            },
            "apps": {},
        }
    )

    session_id_before = await get_session_id()
    await wait_for_expiry(connection_lifetime_secs)

    # This query uses the expired connection, which gets discarded when returned to pool
    await get_session_id()

    # This query gets a fresh connection
    session_id_after = await get_session_id()

    assert session_id_before != session_id_after, (
        "Connection should be recycled after pool lifetime expiry"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_concurrent_queries_use_separate_connections(backend: str):
    """Test that concurrent queries use different pool connections."""
    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend}",
                    "credentials": {
                        "host": CLUSTER_ENDPOINT,
                        "user": CLUSTER_USER,
                        "minsize": 2,
                        "maxsize": 2,
                    },
                }
            },
            "apps": {},
        }
    )

    session_ids = await asyncio.gather(
        get_session_id_with_delay(),
        get_session_id_with_delay(),
    )

    assert session_ids[0] != session_ids[1], "Concurrent queries should use different connections"


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_pool_exhaustion_blocks_until_available(backend: str):
    """Test that requests block when pool is exhausted, then succeed when connection returns."""
    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend}",
                    "credentials": {
                        "host": CLUSTER_ENDPOINT,
                        "user": CLUSTER_USER,
                        "minsize": 1,
                        "maxsize": 1,
                    },
                }
            },
            "apps": {},
        }
    )

    hold_time = 1
    start = asyncio.get_event_loop().time()

    await asyncio.gather(
        get_session_id_with_delay(),  # holds the only connection
        get_session_id(),  # must wait for connection to be released
    )

    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed >= hold_time, "Second query should have waited for connection"
