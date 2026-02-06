# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
A module with custom wrapper that overrides base postgres database operations
adapter in order to make it work with Aurora DSQL.
"""

from django.db.backends.postgresql import operations


class DatabaseOperations(operations.DatabaseOperations):
    def __init__(self, connection):
        super().__init__(connection)
        # Check if using IDENTITY columns
        use_identity = connection.settings_dict.get("USE_SEQUENCE_AUTOFIELDS", False)

        if use_identity:
            # Use bigint for IDENTITY columns
            self.cast_data_types = {
                "AutoField": "bigint",
                "BigAutoField": "bigint",
                "SmallAutoField": "smallint",
            }
        else:
            # Use uuid (default)
            self.cast_data_types = {
                "AutoField": "uuid",
                "BigAutoField": "uuid",
                "SmallAutoField": "smallint",
            }
        self.cast_data_types["SequenceAutoField"] = "bigint"

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
