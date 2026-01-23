# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

__all__ = ["register_backends", "register_asyncpg", "register_psycopg"]

from aurora_dsql_tortoise._version import __version__ as __version__
from aurora_dsql_tortoise.asyncpg import register_backend as register_asyncpg
from aurora_dsql_tortoise.psycopg import register_backend as register_psycopg


def register_backends():
    """Register both asyncpg and psycopg DSQL backends with Tortoise ORM."""
    register_asyncpg()
    register_psycopg()
