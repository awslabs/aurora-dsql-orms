# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
A module with custom wrapper that overrides base postgres database operations
adapter in order to make it work with Aurora DSQL.
"""

from django.db.backends.postgresql import operations


class DatabaseOperations(operations.DatabaseOperations):
    cast_data_types = {
        "AutoField": "uuid",
        "BigAutoField": "uuid",
        "SmallAutoField": "smallint",
    }

    def deferrable_sql(self):
        # Deferrable constraints aren't supported:
        return ""

    def integer_field_range(self, internal_type):
        """
        Override to handle UUIDField which doesn't have integer ranges.
        """
        if internal_type == "UUIDField":
            # Skip validation.
            return None, None
        return super().integer_field_range(internal_type)
