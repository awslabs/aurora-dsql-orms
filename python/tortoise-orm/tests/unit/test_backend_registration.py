# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from tortoise.backends.base.config_generator import DB_LOOKUP


def test_register_psycopg_backend():
    """Test that psycopg backend registers correctly with Tortoise."""
    assert "dsql+psycopg" in DB_LOOKUP
    assert DB_LOOKUP["dsql+psycopg"]["engine"] == "aurora_dsql_tortoise.psycopg"


def test_register_asyncpg_backend():
    """Test that asyncpg backend registers correctly with Tortoise."""
    assert "dsql+asyncpg" in DB_LOOKUP
    assert DB_LOOKUP["dsql+asyncpg"]["engine"] == "aurora_dsql_tortoise.asyncpg"
