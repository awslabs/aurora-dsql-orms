# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from dotenv import load_dotenv

load_dotenv()

cluster_user = os.environ.get("CLUSTER_USER", "admin")
cluster_endpoint = os.environ.get("CLUSTER_ENDPOINT")

if not cluster_endpoint:
    raise ValueError("CLUSTER_ENDPOINT environment variable is not set")

TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "aurora_dsql_tortoise.psycopg",
            "credentials": {
                "host": cluster_endpoint,
                "user": cluster_user,
            },
        }
    },
    "apps": {
        "models": {
            "models": [
                "example.models",
                "aerich.models",
                "aurora_dsql_tortoise.aerich",  # Apply DSQL patches for aerich
            ],
            "default_connection": "default",
        }
    },
}
