# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from tortoise.backends.base.config_generator import expand_db_url


@pytest.mark.parametrize("scheme", ["dsql+psycopg", "dsql+asyncpg"])
def test_url_vmap_entries(scheme):
    """Test that URL components are mapped to correct config keys."""
    config = expand_db_url(f"{scheme}://myuser:mypass@myhost:5432/mydb")
    creds = config["credentials"]
    assert creds["user"] == "myuser"
    assert creds["password"] == "mypass"
    assert creds["host"] == "myhost"
    assert creds["port"] == 5432
    assert creds["database"] == "mydb"


@pytest.mark.parametrize(
    "param,value,expected_type,expected_value",
    [
        ("autocommit", "false", bool, False),
        ("autocommit", "true", bool, True),
        ("close_returns", "false", bool, False),
        ("close_returns", "true", bool, True),
        ("connect_timeout", "12", int, 12),
        ("max_idle", "60.5", float, 60.5),
        ("max_lifetime", "3600.5", float, 3600.5),
        ("max_size", "10", int, 10),
        ("max_waiting", "20", int, 20),
        ("min_size", "5", int, 5),
        ("num_workers", "4", int, 4),
        ("open", "false", bool, False),
        ("open", "true", bool, True),
        ("port", "5432", int, 5432),
        ("prepare_threshold", "5", int, 5),
        ("reconnect_timeout", "30.5", float, 30.5),
        ("timeout", "30", float, 30.0),
        ("token_duration_secs", "120", int, 120),
    ],
)
def test_url_parsing_casts_psycopg(param, value, expected_type, expected_value):
    """Test that string params are cast to correct types for psycopg backend."""
    config = expand_db_url(f"dsql+psycopg://mycluster?{param}={value}")

    assert isinstance(config["credentials"][param], expected_type)
    assert config["credentials"][param] == expected_value


@pytest.mark.parametrize(
    "param,value,expected_type,expected_value",
    [
        ("command_timeout", "30.5", float, 30.5),
        ("direct_tls", "false", bool, False),
        ("direct_tls", "true", bool, True),
        ("max_cacheable_statement_size", "1024", int, 1024),
        ("max_cached_statement_lifetime", "600", float, 600.0),
        ("max_inactive_connection_lifetime", "300.5", float, 300.5),
        ("max_queries", "100", int, 100),
        ("max_size", "10", int, 10),
        ("min_size", "5", int, 5),
        ("port", "5432", int, 5432),
        ("statement_cache_size", "50", int, 50),
        ("timeout", "30", float, 30.0),
        ("token_duration_secs", "120", int, 120),
    ],
)
def test_url_parsing_casts_asyncpg(param, value, expected_type, expected_value):
    """Test that string params are cast to correct types for asyncpg backend."""
    config = expand_db_url(f"dsql+asyncpg://mycluster?{param}={value}")

    assert isinstance(config["credentials"][param], expected_type)
    assert config["credentials"][param] == expected_value
