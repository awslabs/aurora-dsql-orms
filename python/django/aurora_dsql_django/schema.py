# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
This module customizes the default Django database schema editor functions
for Aurora DSQL.
"""

from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.ddl_references import Statement, Table
from django.db.backends.postgresql import schema
from django.db.models import CheckConstraint
from django.db.transaction import TransactionManagementError
from django.db.utils import DatabaseError, NotSupportedError


class ForeignKeyValidation(Statement):
    pass


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

    # Foreign keys created with a table are valid immediately. Foreign keys
    # added later must be created NOT VALID and validated asynchronously.
    sql_create_inline_fk = "REFERENCES %(to_table)s (%(to_column)s) DEFERRABLE INITIALLY DEFERRED"
    sql_create_column_inline_fk = None
    sql_create_fk = (
        "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s FOREIGN KEY (%(column)s) "
        "REFERENCES %(to_table)s (%(to_column)s)%(deferrable)s NOT VALID"
    )
    sql_delete_fk = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    # DSQL requires CHECK constraints added to an existing table to use
    # NOT VALID; the rows are validated afterwards by a separate
    # ALTER TABLE ASYNC ... VALIDATE CONSTRAINT statement (see add_constraint).
    sql_create_check = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s CHECK (%(check)s) NOT VALID"

    # Validate a NOT VALID constraint asynchronously. DSQL runs this as an
    # async DDL job and returns immediately; progress can be tracked via sys.jobs.
    sql_validate_check = "ALTER TABLE ASYNC %(table)s VALIDATE CONSTRAINT %(name)s"
    sql_validate_fk = "ALTER TABLE ASYNC %(table)s VALIDATE CONSTRAINT %(name)s"
    sql_wait_for_job = "CALL sys.wait_for_job(%s)"

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

    def execute(self, sql, params=()):
        if self.collect_sql or not isinstance(sql, ForeignKeyValidation):
            return super().execute(sql, params)
        if self.connection.in_atomic_block and not self.connection.features.can_rollback_ddl:
            raise TransactionManagementError(
                "Executing DDL statements while in a transaction on databases that can't perform a rollback is prohibited."
            )

        sql_text = str(sql)
        with self.connection.cursor() as cursor:
            cursor.execute(sql_text, params)
            job = cursor.fetchone()
            if not job or not job[0]:
                raise DatabaseError("Aurora DSQL constraint validation returned no job ID.")
            cursor.execute(self.sql_wait_for_job, [job[0]])
            status = cursor.fetchone()
            if not status or status[0] is not True:
                succeeded = status[0] if status else None
                raise DatabaseError(
                    f"Aurora DSQL constraint validation job {job[0]} did not succeed (succeeded={succeeded!r})."
                )

    def _defer_fk_validation(self, model, field, suffix):
        self.deferred_sql.append(
            ForeignKeyValidation(
                self.sql_validate_fk,
                table=Table(model._meta.db_table, self.quote_name),
                name=self._fk_constraint_name(model, field, suffix),
            )
        )

    def add_field(self, model, field):
        if not field.many_to_many and field.remote_field and field.db_constraint and not field.null:
            raise NotSupportedError(
                "Aurora DSQL can't add a NOT NULL foreign-key column to an existing "
                "table. Add the field with null=True, backfill it, and keep it nullable."
            )

        super().add_field(model, field)
        if (
            not field.many_to_many
            and field.remote_field
            and field.db_constraint
            and self.connection.features.supports_foreign_keys
        ):
            suffix = "_fk_%(to_table)s_%(to_column)s"
            self._defer_fk_validation(model, field, suffix)

    def _alter_field(
        self,
        model,
        old_field,
        new_field,
        old_type,
        new_type,
        old_db_params,
        new_db_params,
        strict=False,
    ):
        fk_was_dropped = (
            self.connection.features.supports_foreign_keys
            and old_field.remote_field
            and old_field.db_constraint
            and self._field_should_be_altered(
                old_field,
                new_field,
                ignore={"db_comment"},
            )
        )
        fk_was_added = not old_field.remote_field or not old_field.db_constraint

        super()._alter_field(
            model,
            old_field,
            new_field,
            old_type,
            new_type,
            old_db_params,
            new_db_params,
            strict,
        )

        if (
            self.connection.features.supports_foreign_keys
            and new_field.remote_field
            and new_field.db_constraint
            and (fk_was_dropped or fk_was_added)
        ):
            self._defer_fk_validation(
                model,
                new_field,
                "_fk_%(to_table)s_%(to_column)s",
            )

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
