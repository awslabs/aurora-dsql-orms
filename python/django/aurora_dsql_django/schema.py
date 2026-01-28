# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
This module customizes the default Django database schema editor functions
for Aurora DSQL.
"""

from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.postgresql import schema
from django.db.models import CheckConstraint


class DatabaseSchemaEditor(schema.DatabaseSchemaEditor):
    """
    Aurora DSQL schema editor based on the PostgreSQL backend.

    Aurora DSQL is PostgreSQL-compatible but supports a subset of PostgreSQL
    operations. This class overrides SQL templates and methods to work within
    DSQL's constraints.
    """

    # Use DSQL's async index creation syntax.
    sql_create_index = "CREATE INDEX ASYNC %(name)s ON %(table)s%(using)s (%(columns)s)%(include)s%(extra)s%(condition)s"

    # Create unique constraints as unique indexes instead of using "ALTER TABLE".
    sql_create_unique = "CREATE UNIQUE INDEX ASYNC %(name)s ON %(table)s (%(columns)s)"

    # Delete unique constraints by dropping the underlying index.
    sql_delete_unique = "DROP INDEX %(name)s CASCADE"

    # Remove constraint management from default updates.
    sql_update_with_default = "UPDATE %(table)s SET %(column)s = %(default)s WHERE %(column)s IS NULL"

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
            return
        super().add_index(model, index, concurrently)

    def remove_index(self, model, index, concurrently=False):
        if index.contains_expressions and not self.connection.features.supports_expression_indexes:
            return
        super().remove_index(model, index, concurrently)

    def _check_sql(self, name, check):
        # There is no feature check in the upstream implementation when creating
        # a model, so we add our own check.
        if not self.connection.features.supports_table_check_constraints:
            return None
        return super()._check_sql(name, check)

    def add_constraint(self, model, constraint):
        # Older versions of Django don't reference supports_table_check_constraints, so we add this as a backup.
        if isinstance(constraint, CheckConstraint) and not self.connection.features.supports_table_check_constraints:
            return
        super().add_constraint(model, constraint)

    def remove_constraint(self, model, constraint):
        # Older versions of Django don't reference supports_table_check_constraints, so we add this as a backup.
        if isinstance(constraint, CheckConstraint) and not self.connection.features.supports_table_check_constraints:
            return
        super().remove_constraint(model, constraint)

    def _index_columns(self, table, columns, col_suffixes, opclasses):
        # Aurora DSQL doesn't support PostgreSQL opclasses.
        return BaseDatabaseSchemaEditor._index_columns(self, table, columns, col_suffixes, opclasses)

    def _create_like_index_sql(self, model, field):
        # Aurora DSQL doesn't support LIKE indexes which use postgres
        # opsclasses
        return None
