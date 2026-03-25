# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
This module customizes the default Django database schema editor functions
for Aurora DSQL.

Aurora DSQL does not support ALTER COLUMN (TYPE, SET/DROP NOT NULL,
SET/DROP DEFAULT) or DROP COLUMN. To handle migrations that require
these operations, this module implements a table-recreation pattern
adapted from Django's SQLite backend.
"""

import copy
import logging
import time

from django.apps.registry import Apps
from django.db import OperationalError
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.ddl_references import Statement
from django.db.backends.postgresql import schema
from django.db.backends.utils import strip_quotes
from django.db.models import CheckConstraint

logger = logging.getLogger(__name__)


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

    def _execute_with_retry(self, fn, max_retries=3, delay=1.0):
        """
        Execute a callable with retries on OC001 (SerializationFailure).

        DSQL may reject DDL that follows another DDL on the same schema
        object because its schema cache hasn't propagated yet. The standard
        fix is to retry after a brief delay.
        """
        for attempt in range(max_retries):
            try:
                return fn()
            except OperationalError:
                if attempt == max_retries - 1:
                    raise
                logger.debug(
                    "OC001 on attempt %d/%d, retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    delay,
                )
                self.connection.close()
                self.connection.ensure_connection()
                time.sleep(delay)

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

    # -------------------------------------------------------------------------
    # Table recreation pattern for unsupported ALTER TABLE operations.
    #
    # Aurora DSQL does not support:
    #   - ALTER COLUMN ... TYPE
    #   - ALTER COLUMN ... SET/DROP NOT NULL
    #   - ALTER COLUMN ... SET/DROP DEFAULT
    #   - DROP COLUMN
    #
    # For migrations that require these, we recreate the table with the new
    # schema and copy data across. This is adapted from Django's SQLite
    # backend (_remake_table) but simplified for DSQL:
    #   - No foreign key handling (DSQL doesn't support FKs)
    #   - No check constraint handling (already skipped via _check_sql)
    #   - Uses quote_value instead of prepare_default (PostgreSQL-style quoting)
    #
    # Transaction safety: since can_rollback_ddl = False, each self.execute()
    # call auto-commits independently. This naturally satisfies DSQL's
    # one-DDL-per-transaction rule without any special transaction handling.
    # -------------------------------------------------------------------------

    def _remake_table(self, model, create_field=None, delete_field=None, alter_fields=None):
        """
        Recreate a table with modified schema.

        This follows the pattern:
          1. Create a table with the updated definition called "new__<table>"
          2. Copy data from the existing table to the new table
          3. Drop the old table
          4. Rename the new table to the original name
          5. Restore indexes via deferred SQL
        """
        # Work out the new fields dict / mapping
        body = {f.name: f for f in model._meta.local_concrete_fields}
        # Since mapping might mix column names and default values,
        # its values must be already quoted.
        mapping = {f.column: self.quote_name(f.column) for f in model._meta.local_concrete_fields if f.generated is False}
        # This maps field names (not columns) for things like unique_together
        rename_mapping = {}
        # If any of the new or altered fields is introducing a new PK,
        # remove the old one
        restore_pk_field = None
        alter_fields = alter_fields or []
        if getattr(create_field, "primary_key", False) or any(
            getattr(new_field, "primary_key", False) for _, new_field in alter_fields
        ):
            for name, field in list(body.items()):
                if field.primary_key and not any(name == new_field.name for _, new_field in alter_fields):
                    field.primary_key = False
                    restore_pk_field = field
                    if field.auto_created:
                        del body[name]
                        del mapping[field.column]
        # Add in any created fields
        if create_field:
            body[create_field.name] = create_field
            # Choose a default and insert it into the copy map
            if (
                not create_field.has_db_default()
                and not (create_field.many_to_many or create_field.generated)
                and create_field.concrete
            ):
                mapping[create_field.column] = self.quote_value(self.effective_default(create_field))
        # Add in any altered fields
        for alter_field in alter_fields:
            old_field, new_field = alter_field
            body.pop(old_field.name, None)
            mapping.pop(old_field.column, None)
            body[new_field.name] = new_field
            rename_mapping[old_field.name] = new_field.name
            if new_field.generated:
                continue
            if old_field.null and not new_field.null:
                # Transitioning from NULL to NOT NULL — use coalesce to fill
                # existing NULLs with the new default.
                if not new_field.has_db_default():
                    default = self.quote_value(self.effective_default(new_field))
                else:
                    default, _ = self.db_default_sql(new_field)
                case_sql = f"coalesce({self.quote_name(old_field.column)}, {default})"
                mapping[new_field.column] = case_sql
            else:
                mapping[new_field.column] = self.quote_name(old_field.column)
        # Remove any deleted fields
        if delete_field:
            del body[delete_field.name]
            mapping.pop(delete_field.column, None)
            # Remove any implicit M2M tables
            if delete_field.many_to_many and delete_field.remote_field.through._meta.auto_created:
                return self.delete_model(delete_field.remote_field.through)
        # Work inside a new app registry
        apps = Apps()

        # Work out the new value of unique_together, taking renames into
        # account
        unique_together = [[rename_mapping.get(n, n) for n in unique] for unique in model._meta.unique_together]

        indexes = model._meta.indexes
        if delete_field:
            indexes = [index for index in indexes if delete_field.name not in index.fields]

        constraints = list(model._meta.constraints)

        # Provide isolated instances of the fields to the new model body so
        # that the existing model's internals aren't interfered with when
        # the dummy model is constructed.
        body_copy = copy.deepcopy(body)

        # Construct a new model for FK resolution (never materialized as a table).
        meta_contents = {
            "app_label": model._meta.app_label,
            "db_table": model._meta.db_table,
            "unique_together": unique_together,
            "indexes": indexes,
            "constraints": constraints,
            "apps": apps,
        }
        meta = type("Meta", (), meta_contents)
        body_copy["Meta"] = meta
        body_copy["__module__"] = model.__module__
        type(model._meta.object_name, model.__bases__, body_copy)

        # Construct a model with a renamed table name.
        body_copy = copy.deepcopy(body)
        meta_contents = {
            "app_label": model._meta.app_label,
            "db_table": f"new__{strip_quotes(model._meta.db_table)}",
            "unique_together": unique_together,
            "indexes": indexes,
            "constraints": constraints,
            "apps": apps,
        }
        meta = type("Meta", (), meta_contents)
        body_copy["Meta"] = meta
        body_copy["__module__"] = model.__module__
        new_model = type(f"New{model._meta.object_name}", model.__bases__, body_copy)

        # Drop any leftover temp table from a previous failed _remake_table.
        self.execute(
            f"DROP TABLE IF EXISTS {self.quote_name(new_model._meta.db_table)}"
        )

        # Create a new table with the updated schema.
        self.create_model(new_model)

        # Copy data from the old table into the new table
        self.execute(
            "INSERT INTO {} ({}) SELECT {} FROM {}".format(
                self.quote_name(new_model._meta.db_table),
                ", ".join(self.quote_name(x) for x in mapping),
                ", ".join(mapping.values()),
                self.quote_name(model._meta.db_table),
            )
        )

        # Delete the old table
        self.delete_model(model, handle_autom2m=False)

        # Rename the new table to the original name.
        # The preceding DROP may trigger an OC001 (SerializationFailure)
        # because DSQL's schema cache hasn't propagated yet. Retry briefly.
        self._execute_with_retry(
            lambda: self.alter_db_table(
                new_model,
                new_model._meta.db_table,
                model._meta.db_table,
            )
        )

        # Run deferred SQL (indexes) on the correctly-named table.
        # Each execute() auto-commits (can_rollback_ddl = False), so each
        # CREATE INDEX ASYNC runs in its own transaction as DSQL requires.
        for sql in self.deferred_sql:
            self._execute_with_retry(lambda sql=sql: self.execute(sql))
        self.deferred_sql = []
        # Fix any PK-removed field
        if restore_pk_field:
            restore_pk_field.primary_key = True

    def delete_model(self, model, handle_autom2m=True):
        """Delete a model from the database, with optional M2M handling."""
        if handle_autom2m:
            super().delete_model(model)
        else:
            # Delete the table only (no M2M cleanup) — used by _remake_table.
            self.execute(
                self.sql_delete_table
                % {
                    "table": self.quote_name(model._meta.db_table),
                }
            )
            # Remove all deferred statements referencing the deleted table.
            for sql in list(self.deferred_sql):
                if isinstance(sql, Statement) and sql.references_table(model._meta.db_table):
                    self.deferred_sql.remove(sql)

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
        """
        Perform a physical (non-ManyToMany) field update.

        Aurora DSQL does not support ALTER COLUMN operations (TYPE changes,
        nullability changes, default changes). Use RENAME COLUMN for pure
        renames; otherwise recreate the table.
        """
        # Use "ALTER TABLE ... RENAME COLUMN" if only the column name changed.
        if old_field.column != new_field.column and self.column_sql(model, old_field) == self.column_sql(model, new_field):
            return self.execute(self._rename_field_sql(model._meta.db_table, old_field, new_field, new_type))
        # Everything else: recreate the table.
        self._remake_table(model, alter_fields=[(old_field, new_field)])

    def add_field(self, model, field):
        """
        Add a field to a model.

        Aurora DSQL's ADD COLUMN only supports 'column_name data_type' — no
        DEFAULT, NOT NULL, UNIQUE, or PRIMARY KEY inline. Fields requiring
        any of these use table recreation instead.
        """
        from django.db.models.expressions import Value

        # M2M fields create a separate through table.
        if field.many_to_many and field.remote_field.through._meta.auto_created:
            self.create_model(field.remote_field.through)
        elif (
            field.primary_key
            or field.unique
            or not field.null
            or self.effective_default(field) is not None
            or (field.has_db_default() and not isinstance(field.db_default, Value))
        ):
            self._remake_table(model, create_field=field)
        else:
            super().add_field(model, field)

    def remove_field(self, model, field):
        """
        Remove a field from a model.

        Aurora DSQL does not support ALTER TABLE DROP COLUMN, so non-M2M
        field removal requires table recreation.
        """
        # M2M fields are a special case — just drop the through table.
        if field.many_to_many:
            if field.remote_field.through._meta.auto_created:
                self.delete_model(field.remote_field.through)
            return
        # It might not actually have a column behind it
        if field.db_parameters(connection=self.connection)["type"] is None:
            return
        self._remake_table(model, delete_field=field)
