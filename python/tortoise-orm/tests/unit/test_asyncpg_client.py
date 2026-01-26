# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, patch

import pytest

from aurora_dsql_tortoise.asyncpg.client import AuroraDSQLAsyncpgClient
from tests.unit.conftest import TEST_HOST, TEST_USER

DSQL_CONNECTOR_PARAMS = [
    ("region", "us-east-1"),
    ("token_duration_secs", 300),
    ("profile", "myprofile"),
    ("custom_credentials_provider", MagicMock()),
]


@pytest.fixture
def captured_kwargs():
    """Fixture to capture kwargs passed to dsql.create_pool."""
    return {"kwargs": {}}


@pytest.fixture
def mock_create_pool(captured_kwargs):
    """Mock dsql.create_pool to capture kwargs."""

    async def capture_create_pool(dsn, **kwargs):
        captured_kwargs["kwargs"] = kwargs
        return MagicMock()

    with patch("aurora_dsql_tortoise.asyncpg.client.dsql.create_pool", capture_create_pool):
        yield


def create_client(**kwargs):
    """Create a client with required params."""
    return AuroraDSQLAsyncpgClient(connection_name="default", **kwargs)


def pool_kwargs(**extra):
    """Build kwargs as tortoise would pass to create_pool."""
    return {"host": TEST_HOST, "user": TEST_USER, **extra}


@pytest.mark.asyncio
@pytest.mark.parametrize("param,value", DSQL_CONNECTOR_PARAMS)
async def test_connector_param_from_pool_kwargs_only(
    param, value, mock_create_pool, captured_kwargs
):
    """Test that DSQL connector params work when only passed to create_pool."""
    client = create_client()

    await client.create_pool(**pool_kwargs(**{param: value}))

    assert captured_kwargs["kwargs"][param] == value


@pytest.mark.asyncio
@pytest.mark.parametrize("param,value", DSQL_CONNECTOR_PARAMS)
async def test_connector_param_from_client_extra(param, value, mock_create_pool, captured_kwargs):
    """Test that DSQL connector params from client constructor end up in create_pool."""
    client = create_client(**{param: value})

    await client.create_pool(**pool_kwargs())

    assert captured_kwargs["kwargs"][param] == value


@pytest.mark.asyncio
@pytest.mark.parametrize("param,value", DSQL_CONNECTOR_PARAMS)
async def test_connector_param_pool_kwargs_overrides_client(
    param, value, mock_create_pool, captured_kwargs
):
    """Test that pool kwargs take precedence over client constructor."""
    client = create_client(**{param: "default"})

    await client.create_pool(**pool_kwargs(**{param: value}))

    assert captured_kwargs["kwargs"][param] == value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "param,value",
    [
        ("max_inactive_connection_lifetime", 60),
        ("min_size", 1),
        ("max_size", 5),
    ],
)
async def test_pool_param_passed_to_create_pool(param, value, mock_create_pool, captured_kwargs):
    """Test that pool params are passed through to dsql.create_pool."""
    client = create_client()

    await client.create_pool(**pool_kwargs(**{param: value}))

    assert param in captured_kwargs["kwargs"], f"{param} should be passed to dsql.create_pool"
