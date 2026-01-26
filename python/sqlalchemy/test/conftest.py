# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import re

from dotenv import load_dotenv
from sqlalchemy.dialects import registry
from sqlalchemy.testing import engines

from aurora_dsql_sqlalchemy import create_dsql_engine

load_dotenv()

CLUSTER_ENDPOINT = os.environ.get("CLUSTER_ENDPOINT")
CLUSTER_USER = os.environ.get("CLUSTER_USER", "admin")
DRIVER = os.environ.get("DRIVER", "psycopg")

match = re.match(
    r"^([a-z0-9]+)\.dsql(?:-[^.]+)?\.([a-z0-9-]+)\.on\.aws$", CLUSTER_ENDPOINT or ""
)
if not match:
    raise ValueError(f"Invalid CLUSTER_ENDPOINT format: {CLUSTER_ENDPOINT}")
CLUSTER_ID, REGION = match.groups()

# Register your dialect
registry.register(
    "auroradsql",
    "aurora_dsql_sqlalchemy.psycopg2",
    "AuroraDSQLDialect_psycopg2",
)
registry.register(
    "auroradsql.psycopg2",
    "aurora_dsql_sqlalchemy.psycopg2",
    "AuroraDSQLDialect_psycopg2",
)

registry.register(
    "auroradsql.psycopg",
    "aurora_dsql_sqlalchemy.psycopg",
    "AuroraDSQLDialect_psycopg",
)


def custom_testing_engine(url=None, options=None, *, asyncio=False):
    print(f"Creating DSQL engine for {CLUSTER_ENDPOINT} with driver {DRIVER}")
    assert CLUSTER_ENDPOINT is not None

    engine = create_dsql_engine(
        host=CLUSTER_ENDPOINT,
        user=CLUSTER_USER,
        driver=DRIVER,
    )

    return engine


engines.testing_engine = custom_testing_engine

# Import SQLAlchemy testing components
from sqlalchemy.testing.plugin.pytestplugin import *  # noqa # type: ignore[reportWildcardImportFromLibrary]
