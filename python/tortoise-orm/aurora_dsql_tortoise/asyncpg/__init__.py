# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aurora_dsql_tortoise.common.config import ASYNCPG_CASTS
from aurora_dsql_tortoise.common.config import register_backend as _register_backend

from .client import AuroraDSQLAsyncpgClient

# Required by Tortoise when using engine="aurora_dsql_tortoise.asyncpg"
client_class = AuroraDSQLAsyncpgClient


def register_backend():
    """Register the 'dsql+asyncpg' URL scheme with Tortoise ORM."""
    _register_backend(__name__, ASYNCPG_CASTS)
