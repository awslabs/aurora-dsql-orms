# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os

from aurora_dsql_tortoise import register_backends

if os.environ.get("DEBUG"):
    logging.basicConfig(format="%(name)s - %(message)s")
    logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)

BACKENDS = ["psycopg", "asyncpg"]

register_backends()
