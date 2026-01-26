# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aurora_dsql_tortoise.common.config import PSYCOPG_CASTS
from aurora_dsql_tortoise.common.config import register_backend as _register_backend

from .client import AuroraDSQLPsycopgClient

# Required by Tortoise when using engine="aurora_dsql_tortoise.psycopg"
client_class = AuroraDSQLPsycopgClient


def register_backend():
    """Register the 'dsql+psycopg' URL scheme with Tortoise ORM."""
    _register_backend(__name__, PSYCOPG_CASTS)
