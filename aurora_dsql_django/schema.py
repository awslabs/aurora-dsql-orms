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
This module customizes the default Django database schema editor functions
for Aurora DSQL.
"""

from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.postgresql import schema


class DatabaseSchemaEditor(schema.DatabaseSchemaEditor):
    """
    Aurora DSQL schema editor based on the PostgreSQL backend.
    
    Aurora DSQL is PostgreSQL-compatible but supports a subset of PostgreSQL
    operations. This class overrides SQL templates and methods to work within
    DSQL's constraints.
    """

    # Use DSQL's async index creation syntax.
    sql_create_index = (
        "CREATE INDEX ASYNC %(name)s ON %(table)s%(using)s "
        "(%(columns)s)%(include)s%(extra)s%(condition)s"
    )

    # Create unique constraints as unique indexes instead of using "ALTER TABLE".
    sql_create_unique = "CREATE UNIQUE INDEX ASYNC %(name)s ON %(table)s (%(columns)s)"

    # Delete unique constraints by dropping the underlying index.
    sql_delete_unique = "DROP INDEX %(name)s CASCADE"

    # Remove constraint management from default updates.
    sql_update_with_default = (
        "UPDATE %(table)s SET %(column)s = %(default)s WHERE %(column)s IS NULL"
    )

    # These "ALTER TABLE" operations are not supported.
    sql_create_pk = ""
    sql_create_fk = ""
    sql_delete_fk = ""
    sql_create_check = ""
    sql_delete_check = ""
    sql_delete_constraint = ""
    sql_delete_column = ""

    def __enter__(self):
        super().__enter__()
        # As long as DatabaseFeatures.can_rollback_ddl = False, compose() may
        # fail if connection is None as per
        # https://github.com/django/django/pull/15687#discussion_r1038175823.
        # See also
        # https://github.com/django/django/pull/15687#discussion_r1041503991.
        self.connection.ensure_connection()
        return self

    def add_index(self, model, index, concurrently=False):
        if index.contains_expressions and not self.connection.features.supports_expression_indexes:
            return None
        super().add_index(model, index, concurrently)

    def remove_index(self, model, index, concurrently=False):
        if index.contains_expressions and not self.connection.features.supports_expression_indexes:
            return None
        super().remove_index(model, index, concurrently)

    def _index_columns(self, table, columns, col_suffixes, opclasses):
        # Aurora DSQL doesn't support PostgreSQL opclasses.
        return BaseDatabaseSchemaEditor._index_columns(
            self, table, columns, col_suffixes, opclasses
        )

    def _create_like_index_sql(self, model, field):
        # Aurora DSQL doesn't support LIKE indexes which use postgres
        # opsclasses
        return None
