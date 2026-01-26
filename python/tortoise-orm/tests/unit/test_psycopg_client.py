# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import aurora_dsql_psycopg as dsql
import psycopg
import pytest

from aurora_dsql_tortoise.psycopg.client import AuroraDSQLPsycopgClient
from tests.unit.conftest import TEST_HOST, TEST_USER

DSQL_CONNECTOR_PARAMS = [
    ("region", "us-east-1"),
    ("token_duration_secs", 300),
    ("profile", "myprofile"),
    ("custom_credentials_provider", MagicMock()),
]


@pytest.fixture
def captured_kwargs():
    """Fixture to capture kwargs passed to pool and connection."""
    return {"pool": {}, "conn": {}, "connection_class": None}


@pytest.fixture
def mock_pool(captured_kwargs):
    """Mock AsyncConnectionPool to capture initialization kwargs."""

    def capture_init(self, conninfo, *, connection_class, kwargs, open, **pool_kwargs):
        captured_kwargs["pool"] = pool_kwargs
        captured_kwargs["conn"] = kwargs
        captured_kwargs["connection_class"] = connection_class

    with patch("aurora_dsql_tortoise.psycopg.client.AsyncConnectionPool.__init__", capture_init):
        with patch(
            "aurora_dsql_tortoise.psycopg.client.AsyncConnectionPool.open", new_callable=AsyncMock
        ):
            yield


def create_client(**kwargs):
    """Create a client with required params."""
    return AuroraDSQLPsycopgClient(connection_name="default", **kwargs)


def pool_kwargs(**extra):
    """Build kwargs as tortoise would pass to create_pool."""
    return {
        "conninfo": f"host={TEST_HOST} user={TEST_USER}",
        "kwargs": {},
        "connection_class": None,
        **extra,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("param,value", DSQL_CONNECTOR_PARAMS)
async def test_connector_param_from_pool_kwargs_only(param, value, mock_pool, captured_kwargs):
    """Test that DSQL connector params work when only passed to create_pool."""
    client = create_client()  # no param in constructor

    await client.create_pool(**pool_kwargs(**{param: value}))

    assert captured_kwargs["conn"][param] == value
    assert param not in captured_kwargs["pool"]


@pytest.mark.asyncio
@pytest.mark.parametrize("param,value", DSQL_CONNECTOR_PARAMS)
async def test_connector_param_from_client_extra(param, value, mock_pool, captured_kwargs):
    """Test that DSQL connector params from client constructor end up in connection kwargs."""
    client = create_client(**{param: value})

    await client.create_pool(**pool_kwargs())

    assert captured_kwargs["conn"][param] == value
    assert param not in captured_kwargs["pool"]


@pytest.mark.asyncio
@pytest.mark.parametrize("param,value", DSQL_CONNECTOR_PARAMS)
async def test_connector_param_from_pool_kwargs_overrides(param, value, mock_pool, captured_kwargs):
    """Test that DSQL connector params in pool kwargs override client params."""
    client = create_client(**{param: "default"})

    await client.create_pool(**pool_kwargs(**{param: value}))

    assert captured_kwargs["conn"][param] == value
    assert param not in captured_kwargs["pool"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "param,value",
    [
        ("max_lifetime", 60),
        ("timeout", 30),
        ("min_size", 1),
        ("max_size", 5),
    ],
)
async def test_pool_param_passed_to_pool(param, value, mock_pool, captured_kwargs):
    """Test that pool params are passed to pool kwargs."""
    client = create_client()

    await client.create_pool(**pool_kwargs(**{param: value}))

    assert param in captured_kwargs["pool"], f"{param} should be in pool kwargs"
    assert param not in captured_kwargs["conn"], f"{param} should be in connection kwargs"


@pytest.mark.asyncio
async def test_conninfo_merged_into_connection_kwargs(mock_pool, captured_kwargs):
    """Test that conninfo string values end up in connection kwargs."""
    client = create_client()

    await client.create_pool(**pool_kwargs())

    assert captured_kwargs["conn"]["host"] == TEST_HOST
    assert captured_kwargs["conn"]["user"] == TEST_USER


@pytest.mark.asyncio
async def test_preexisting_kwargs_preserved(mock_pool, captured_kwargs):
    """Test that pre-existing values in kwargs dict are preserved."""
    client = create_client()
    existing_value = "existing_value"

    await client.create_pool(**pool_kwargs(kwargs={"existing_key": existing_value}))

    assert captured_kwargs["conn"]["existing_key"] == existing_value
    assert captured_kwargs["conn"]["host"] == TEST_HOST  # conninfo preserved


@pytest.mark.asyncio
async def test_psycopg_async_connection_replaced_with_dsql(mock_pool, captured_kwargs):
    """Test that psycopg.AsyncConnection is treated as default and replaced.

    The parent PsycopgClient hardcodes psycopg.AsyncConnection in _template,
    so we treat it as "no custom class" and replace with DSQLAsyncConnection.
    """
    client = create_client()

    await client.create_pool(**pool_kwargs(connection_class=psycopg.AsyncConnection))

    assert captured_kwargs["connection_class"] is dsql.DSQLAsyncConnection


@pytest.mark.asyncio
async def test_non_subclass_connection_class_warns_but_used(mock_pool, captured_kwargs):
    """Test that non-subclass connection_class triggers warning but is still used."""

    class CustomConnection:
        pass

    client = create_client()

    with pytest.warns(UserWarning, match="not a subclass of DSQLAsyncConnection"):
        await client.create_pool(**pool_kwargs(connection_class=CustomConnection))

    assert captured_kwargs["connection_class"] is CustomConnection


@pytest.mark.asyncio
async def test_valid_connection_class_subclass_used(mock_pool, captured_kwargs):
    """Test that a valid DSQLAsyncConnection subclass is used without warning."""

    class CustomConnection(dsql.DSQLAsyncConnection):
        pass

    client = create_client()

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        await client.create_pool(**pool_kwargs(connection_class=CustomConnection))

    assert captured_kwargs["connection_class"] is CustomConnection


@pytest.mark.asyncio
async def test_default_connection_class(mock_pool, captured_kwargs):
    """Test that DSQLAsyncConnection is used when no connection_class is provided."""
    client = create_client()

    await client.create_pool(**pool_kwargs())

    assert captured_kwargs["connection_class"] is dsql.DSQLAsyncConnection
