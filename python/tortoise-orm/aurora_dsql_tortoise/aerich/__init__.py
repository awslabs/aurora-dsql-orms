# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Aerich compatibility patches for Aurora DSQL.

Add "aurora_dsql_tortoise.aerich" to your models list to auto-apply patches:

    "apps": {
        "models": {
            "models": ["your.models", "aerich.models", "aurora_dsql_tortoise.aerich"],
        }
    }
"""

from aurora_dsql_tortoise.aerich import patch as patch
