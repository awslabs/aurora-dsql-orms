# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with
# the License. A copy of the License is located at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file.
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.

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
