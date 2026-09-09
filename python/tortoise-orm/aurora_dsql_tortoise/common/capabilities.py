# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from tortoise.backends.base.client import Capabilities


def dsql_capabilities(postgres_capabilities: Capabilities) -> Capabilities:
    """Copy PostgreSQL capabilities while disabling unsupported lock clauses."""
    values = vars(postgres_capabilities).copy()
    values.pop("_mutable", None)
    dialect = values.pop("dialect")
    values["support_for_update"] = True
    values["support_for_no_key_update"] = False
    return Capabilities(dialect, **values)
