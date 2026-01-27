# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import boto3
import pytest
from botocore.credentials import CredentialProvider
from tortoise import Tortoise

from tests.conftest import BACKENDS

from .conftest import (
    CLUSTER_ENDPOINT,
    CLUSTER_ID,
    CLUSTER_USER,
    REGION,
    assert_connection_works,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_connection_with_engine(backend: str):
    """Test connection using explicit engine config."""
    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend}",
                    "credentials": {"host": CLUSTER_ENDPOINT, "user": CLUSTER_USER},
                }
            },
            "apps": {},
        }
    )
    await assert_connection_works()


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_connection_with_cluster_id_and_region(backend: str):
    """Test connection with cluster ID and region instead of full endpoint."""
    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend}",
                    "credentials": {"host": CLUSTER_ID, "user": CLUSTER_USER, "region": REGION},
                }
            },
            "apps": {},
        }
    )
    await assert_connection_works()


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_connection_with_cluster_id_and_default_region(backend: str, monkeypatch):
    """Test that AWS_DEFAULT_REGION env var is used when only cluster ID is provided."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend}",
                    "credentials": {"host": CLUSTER_ID, "user": CLUSTER_USER},
                }
            },
            "apps": {},
        }
    )
    await assert_connection_works()


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_connection_with_url(backend: str):
    """Test connection using dsql+{backend}:// URL."""
    await Tortoise.init(
        config={
            "connections": {"default": f"dsql+{backend}://{CLUSTER_USER}@{CLUSTER_ENDPOINT}"},
            "apps": {},
        }
    )
    await assert_connection_works()


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_connection_with_url_cluster_id_and_region(backend: str):
    """Test connection using URL with cluster ID and region param."""
    await Tortoise.init(
        config={
            "connections": {
                "default": f"dsql+{backend}://{CLUSTER_USER}@{CLUSTER_ID}?region={REGION}"
            },
            "apps": {},
        }
    )
    await assert_connection_works()


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_connection_with_url_cluster_id_and_default_region(backend: str, monkeypatch):
    """Test that AWS_DEFAULT_REGION env var is used when only cluster ID is provided via URL."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    await Tortoise.init(
        config={
            "connections": {"default": f"dsql+{backend}://{CLUSTER_USER}@{CLUSTER_ID}"},
            "apps": {},
        }
    )
    await assert_connection_works()


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_connection_with_default_admin_user(backend: str):
    """Test connection works without explicit user when default is admin."""
    if CLUSTER_USER != "admin":
        pytest.skip("Test only runs when CLUSTER_USER is admin")

    await Tortoise.init(
        config={
            "connections": {"default": f"dsql+{backend}://{CLUSTER_ENDPOINT}"},
            "apps": {},
        }
    )
    await assert_connection_works()


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_profile_setting_used_for_credentials(backend: str, monkeypatch):
    """Test that profile setting is passed to boto3.Session for credentials."""
    test_profile = "test-profile"
    captured_profile = None
    original_session = boto3.Session

    def mock_session(*args, **kwargs):
        nonlocal captured_profile
        captured_profile = kwargs.get("profile_name")
        kwargs.pop("profile_name", None)
        return original_session(*args, **kwargs)

    monkeypatch.setattr("boto3.Session", mock_session)
    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend}",
                    "credentials": {
                        "host": CLUSTER_ENDPOINT,
                        "user": CLUSTER_USER,
                        "profile": test_profile,
                    },
                }
            },
            "apps": {},
        }
    )
    await assert_connection_works()

    assert captured_profile == test_profile, (
        f"Expected profile '{test_profile}' to be passed to boto3.Session, got '{captured_profile}'"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_profile_url_parameter_used_for_credentials(backend: str, monkeypatch):
    """Test that profile setting works when passed via connection URL."""
    test_profile = "test-profile"
    captured_profile = None
    original_session = boto3.Session

    def mock_session(*args, **kwargs):
        nonlocal captured_profile
        captured_profile = kwargs.get("profile_name")
        kwargs.pop("profile_name", None)
        return original_session(*args, **kwargs)

    monkeypatch.setattr("boto3.Session", mock_session)
    await Tortoise.init(
        config={
            "connections": {
                "default": f"dsql+{backend}://{CLUSTER_USER}@{CLUSTER_ENDPOINT}?profile={test_profile}"
            },
            "apps": {},
        }
    )
    await assert_connection_works()

    assert captured_profile == test_profile, (
        f"Expected profile '{test_profile}' to be passed to boto3.Session, got '{captured_profile}'"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_custom_credentials_provider_passed_to_connector(backend: str):
    """Test that custom_credentials_provider is passed through to the python connector."""

    class TestCredentialProvider(CredentialProvider):
        METHOD = "test-provider"

        def __init__(self):
            super().__init__(self)
            self.load_called = False

        def load(self):
            self.load_called = True
            return boto3.Session().get_credentials()

    provider = TestCredentialProvider()

    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": f"aurora_dsql_tortoise.{backend}",
                    "credentials": {
                        "host": CLUSTER_ENDPOINT,
                        "user": CLUSTER_USER,
                        "custom_credentials_provider": provider,
                    },
                }
            },
            "apps": {},
        }
    )
    await assert_connection_works()

    assert provider.load_called, "custom_credentials_provider.load() was not called"
