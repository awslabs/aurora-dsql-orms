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

    # DSQL requires CHECK constraints added to an existing table to use
    # NOT VALID; the rows are validated afterwards by a separate
    # ALTER TABLE ASYNC ... VALIDATE CONSTRAINT statement (see add_constraint).
    sql_create_check = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s CHECK (%(check)s) NOT VALID"

    # Validate a NOT VALID constraint asynchronously. DSQL runs this as an
    # async DDL job and returns immediately; progress can be tracked via sys.jobs.
    sql_validate_check = "ALTER TABLE ASYNC %(table)s VALIDATE CONSTRAINT %(name)s"

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

    def add_constraint(self, model, constraint):
        # DSQL adds a CHECK constraint to an existing table with NOT VALID
        # (see sql_create_check), then validates existing rows asynchronously.
        # Emit the VALIDATE CONSTRAINT ASYNC statement as a follow-up so the
        # constraint is enforced against the data already in the table.
        super().add_constraint(model, constraint)
        if isinstance(constraint, CheckConstraint):
            self.execute(
                self.sql_validate_check
                % {
                    "table": self.quote_name(model._meta.db_table),
                    "name": self.quote_name(constraint.name),
                }
            )

    def _index_columns(self, table, columns, col_suffixes, opclasses):
        # Aurora DSQL doesn't support PostgreSQL opclasses.
        return BaseDatabaseSchemaEditor._index_columns(self, table, columns, col_suffixes, opclasses)

    def _create_like_index_sql(self, model, field):
        # Aurora DSQL doesn't support LIKE indexes which use postgres
        # opsclasses
        return None
