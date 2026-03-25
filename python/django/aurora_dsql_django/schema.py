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
import re
import time

from django.apps.registry import Apps
from django.db import OperationalError, ProgrammingError
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.ddl_references import Statement
from django.db.backends.postgresql import schema
from django.db.backends.utils import strip_quotes
from django.db.models import CheckConstraint

logger = logging.getLogger(__name__)

# OCC retry settings for DSQL schema operations.
_OCC_MAX_RETRIES = 3
_OCC_RETRY_DELAY = 1.0

# DSQL has a 3000 row limit per transaction. Use a smaller batch size
# to stay well within the limit when copying data during table recreation.
_COPY_BATCH_SIZE = 1000


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

    @staticmethod
    def _get_sqlstate(exc):
        """Extract the PostgreSQL sqlstate from a Django database exception."""
        cause = getattr(exc, "__cause__", None)
        return getattr(cause, "sqlstate", None)

    @classmethod
    def _is_occ_error(cls, exc):
        """Check whether an OperationalError is a DSQL OCC conflict (OC000/OC001)."""
        return cls._get_sqlstate(exc) in ("OC000", "OC001")

    def execute(self, sql, params=()):
        """
        Execute SQL with automatic retry on DSQL OCC errors.

        DSQL may reject operations with SerializationFailure (OC000/OC001)
        when concurrent schema changes conflict. Since can_rollback_ddl=False,
        each execute() auto-commits independently, making retries safe.

        Also handles "already exists" errors on CREATE INDEX ASYNC statements.
        DSQL creates indexes asynchronously, and an in-progress ASYNC index
        may survive a DROP TABLE, leaving an orphaned index name. When this
        happens, the existing index is dropped and the CREATE is retried.
        """
        _super_execute = super().execute
        _index_dropped = False

        def _do_execute():
            nonlocal _index_dropped
            try:
                return _super_execute(sql, params)
            except ProgrammingError as e:
                # DSQL's ASYNC index creation can leave orphaned index names
                # that survive DROP TABLE. If a CREATE INDEX hits "already
                # exists" (42P07), drop the stale index and retry once.
                sql_str = str(sql)
                if not _index_dropped and self._get_sqlstate(e) == "42P07" and "INDEX" in sql_str:
                    match = re.search(r"INDEX\s+(?:ASYNC\s+)?(?:IF\s+NOT\s+EXISTS\s+)?(\S+)", sql_str)
                    if match:
                        index_name = strip_quotes(match.group(1))
                        logger.debug("Index %s already exists, dropping and retrying", index_name)
                        self.connection.close()
                        self.connection.ensure_connection()
                        _super_execute(f"DROP INDEX IF EXISTS {self.quote_name(index_name)}")
                        _index_dropped = True
                        return _super_execute(sql, params)
                raise

        return self._occ_retry(_do_execute)

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
        # opclasses
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
    # schema and copy data across. This uses a rename-first pattern to
    # prevent silent data loss from concurrent writes:
    #   0. Recover from any prior failed attempt (detect + rename back)
    #   1. RENAME original → old__<table>  (freezes the source)
    #   2. CREATE new__<table>             (new schema)
    #   3. INSERT INTO new__<table> SELECT FROM old__<table> (batched)
    #   4. DROP old__<table>
    #   5. RENAME new__<table> → original
    #
    # Adapted from Django's SQLite backend but simplified for DSQL:
    #   - No foreign key handling (DSQL doesn't support FKs)
    #   - No check constraint handling (already skipped via _check_sql)
    #   - Uses quote_value instead of prepare_default (PostgreSQL-style quoting)
    #
    # Transaction safety: since can_rollback_ddl = False, each self.execute()
    # call auto-commits independently. This naturally satisfies DSQL's
    # one-DDL-per-transaction rule without any special transaction handling.
    # OCC errors (OC000/OC001) are retried automatically via execute().
    #
    # Data safety: the source table (old__) is kept until the copy is
    # verified by row count. Any failure before that point recovers from
    # old__. After verification, old__ is dropped and any subsequent
    # failure recovers from new__. No path loses data silently.
    #
    # WARNING: This is designed for development iteration, not production
    # use on tables with significant data. The table is unavailable under
    # its original name during the recreation window (between steps 1
    # and 5). For production schema changes, consider blue/green
    # deployments or manual migration strategies.
    # -------------------------------------------------------------------------

    def _occ_retry(self, fn):
        """Run fn() with automatic retry on DSQL OCC errors (OC000/OC001)."""
        for attempt in range(_OCC_MAX_RETRIES):
            try:
                return fn()
            except OperationalError as e:
                if not self._is_occ_error(e) or attempt == _OCC_MAX_RETRIES - 1:
                    raise
                logger.debug(
                    "DSQL OCC error (sqlstate=%s) on attempt %d/%d, retrying in %.1fs",
                    self._get_sqlstate(e),
                    attempt + 1,
                    _OCC_MAX_RETRIES,
                    _OCC_RETRY_DELAY,
                )
                self.connection.close()
                self.connection.ensure_connection()
                time.sleep(_OCC_RETRY_DELAY)

    def _query_with_retry(self, sql, params=None):
        """Execute a read query with OCC retry, returning all rows."""

        def _do_query():
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

        return self._occ_retry(_do_query)

    def _table_exists(self, table_name):
        """Check whether a table exists in the current schema."""
        rows = self._query_with_retry(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = %s",
            [strip_quotes(table_name)],
        )
        return len(rows) > 0

    def _remake_table(self, model, create_field=None, delete_field=None, alter_fields=None):
        """
        Recreate a table with modified schema using the rename-first pattern.

        Aurora DSQL doesn't support ALTER COLUMN or DROP COLUMN. This method
        recreates the table with the new schema. To prevent silent data loss
        from concurrent writes, the original table is renamed first to freeze
        it before copying data.

        The pattern:
          0. Recover from any previous failed _remake_table attempt
          1. Rename the original table to "old__<table>" (freezes writes)
          2. Create "new__<table>" with the updated schema
          3. Copy data from "old__<table>" into "new__<table>" (batched)
          4. Drop "old__<table>"
          5. Rename "new__<table>" to the original name
          6. Restore indexes via deferred SQL

        Availability drops temporarily between steps 1 and 5 (the original
        table name doesn't exist), but no data is silently lost -- writes
        to the old name fail loudly instead of disappearing.

        If the process fails partway through, rerunning ``migrate`` will
        recover automatically: step 0 detects leftover temp tables and
        restores the original table name before proceeding.

        .. warning::

            This is designed for **development and iteration**, not
            production use on tables with significant data. The table is
            unavailable under its original name during the recreation
            window. For production schema changes, consider blue/green
            deployments or manual migration strategies.
        """
        # Deleting an M2M field just drops the through table -- no recreation.
        if delete_field:
            if delete_field.many_to_many and delete_field.remote_field.through._meta.auto_created:
                return self.delete_model(delete_field.remote_field.through)

        # Work out the new fields dict / mapping
        body = {f.name: f for f in model._meta.local_concrete_fields}
        # Since mapping might mix column names and default values,
        # its values must be already quoted.
        mapping = {f.column: self.quote_name(f.column) for f in model._meta.local_concrete_fields if not f.generated}
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
        for old_field, new_field in alter_fields:
            body.pop(old_field.name, None)
            mapping.pop(old_field.column, None)
            body[new_field.name] = new_field
            rename_mapping[old_field.name] = new_field.name
            if new_field.generated:
                continue
            if old_field.null and not new_field.null:
                # Transitioning from NULL to NOT NULL -- use coalesce to fill
                # existing NULLs with the new default.
                if not new_field.has_db_default():
                    default = self.quote_value(self.effective_default(new_field))
                else:
                    default, _ = self.db_default_sql(new_field)
                mapping[new_field.column] = f"coalesce({self.quote_name(old_field.column)}, {default})"
            else:
                mapping[new_field.column] = self.quote_name(old_field.column)
        # Remove any deleted fields
        if delete_field:
            del body[delete_field.name]
            mapping.pop(delete_field.column, None)
        # Work inside a new app registry
        apps = Apps()

        # Work out the new value of unique_together, taking renames into
        # account
        unique_together = [[rename_mapping.get(n, n) for n in unique] for unique in model._meta.unique_together]

        indexes = model._meta.indexes
        if delete_field:
            indexes = [index for index in indexes if delete_field.name not in index.fields]

        constraints = list(model._meta.constraints)
        if delete_field:
            constraints = [
                constraint
                for constraint in constraints
                if not (hasattr(constraint, "fields") and delete_field.name in constraint.fields)
            ]

        # Construct a model with the new__<table> name for creating the new schema.
        # Use deep copies so the existing model's internals aren't modified.
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

        original_table = model._meta.db_table
        old_table = f"old__{strip_quotes(original_table)}"
        new_table = new_model._meta.db_table
        remake_tables = (original_table, old_table, new_table)

        def _clear_deferred_sql_for_remake():
            """Remove deferred SQL referencing any of the three remake tables."""
            self.deferred_sql = [
                sql
                for sql in self.deferred_sql
                if not (isinstance(sql, Statement) and any(sql.references_table(t) for t in remake_tables))
            ]

        # Step 0: Recover from a previous failed _remake_table.
        #
        # If the original table doesn't exist, a prior run failed partway
        # through. Detect the state and recover rather than losing data.
        original_exists = self._table_exists(original_table)
        old_exists = self._table_exists(old_table)
        new_exists = self._table_exists(new_table)

        if not original_exists:
            if new_exists and not old_exists:
                # Failed after DROP old__ but before RENAME new__ → original.
                # new__table has all the data. Just rename it back.
                logger.warning(
                    "Recovering _remake_table for %s: renaming %s back to %s",
                    original_table,
                    new_table,
                    original_table,
                )
                self.execute(f"ALTER TABLE {self.quote_name(new_table)} RENAME TO {self.quote_name(original_table)}")
                _clear_deferred_sql_for_remake()
            elif old_exists:
                # Failed after RENAME original → old__ but before completing.
                # old__table has the data. Rename it back to the original.
                logger.warning(
                    "Recovering _remake_table for %s: renaming %s back to %s",
                    original_table,
                    old_table,
                    original_table,
                )
                self.execute(f"DROP TABLE IF EXISTS {self.quote_name(new_table)}")
                self.execute(f"ALTER TABLE {self.quote_name(old_table)} RENAME TO {self.quote_name(original_table)}")
                _clear_deferred_sql_for_remake()
            else:
                raise RuntimeError(
                    f"Cannot recover _remake_table for '{original_table}': "
                    f"none of '{original_table}', '{old_table}', or "
                    f"'{new_table}' exist. Manual intervention required."
                )
        else:
            # Original table exists. Safe to clean up any leftover temp tables.
            if old_exists:
                self.execute(f"DROP TABLE IF EXISTS {self.quote_name(old_table)}")
            if new_exists:
                self.execute(f"DROP TABLE IF EXISTS {self.quote_name(new_table)}")

        # Remove any pre-existing deferred SQL for the original table
        # (from earlier operations in this schema editor session) before we
        # replace it. create_model() below will generate fresh deferred SQL
        # for the new table, and alter_db_table() will rename those references.
        self.deferred_sql = [
            sql for sql in self.deferred_sql if not (isinstance(sql, Statement) and sql.references_table(original_table))
        ]

        # Step 1: Rename the original table to freeze it against concurrent writes.
        # Any writes to the original table name will now fail loudly.
        self.execute(f"ALTER TABLE {self.quote_name(original_table)} RENAME TO {self.quote_name(old_table)}")

        # Step 2: Create the new table with the updated schema.
        # This adds deferred SQL (indexes) referencing new__<table>.
        # Track where new deferred SQL starts so we only flush what
        # create_model adds, preserving deferred SQL from other tables.
        pre_deferred_count = len(self.deferred_sql)
        self.create_model(new_model)

        # Step 3: Copy data from the frozen old table into the new table.
        # DSQL has a 3000 row limit per transaction. Copy in batches using
        # cursor-based pagination (WHERE pk >= last_pk) for O(n) performance.
        # Each batch auto-commits independently (can_rollback_ddl = False).
        dst_cols = ", ".join(self.quote_name(x) for x in mapping)
        src_exprs = ", ".join(mapping.values())
        q_new = self.quote_name(new_table)
        q_old = self.quote_name(old_table)
        q_pk = self.quote_name(model._meta.pk.column)

        total_rows = self._query_with_retry(f"SELECT COUNT(*) FROM {q_old}")[0][0]

        if total_rows > 0:
            # Seed: fetch the first PK value (MIN() doesn't support UUID).
            last_pk = self._query_with_retry(f"SELECT {q_pk} FROM {q_old} ORDER BY {q_pk} LIMIT 1")[0][0]

            copied = 0
            while copied < total_rows:
                self.execute(
                    f"INSERT INTO {q_new} ({dst_cols})"
                    f" SELECT {src_exprs} FROM {q_old}"
                    f" WHERE {q_pk} >= %s"
                    f" ORDER BY {q_pk}"
                    f" LIMIT {_COPY_BATCH_SIZE}",
                    [last_pk],
                )
                copied += _COPY_BATCH_SIZE
                logger.info(
                    "_remake_table %s: copied %d/%d rows",
                    original_table,
                    min(copied, total_rows),
                    total_rows,
                )
                # Advance the cursor past the batch we just copied.
                rows = self._query_with_retry(
                    f"SELECT {q_pk} FROM {q_old} WHERE {q_pk} >= %s ORDER BY {q_pk} LIMIT 1 OFFSET {_COPY_BATCH_SIZE}",
                    [last_pk],
                )
                if not rows:
                    break  # No more rows
                last_pk = rows[0][0]

            # Verify the copy is complete before dropping the source.
            copied_rows = self._query_with_retry(f"SELECT COUNT(*) FROM {q_new}")[0][0]
            if copied_rows != total_rows:
                # Abort: recover by renaming old__ back to original.
                self.execute(f"DROP TABLE IF EXISTS {q_new}")
                self.execute(f"ALTER TABLE {q_old} RENAME TO {self.quote_name(original_table)}")
                raise RuntimeError(
                    f"_remake_table copy verification failed for "
                    f"'{original_table}': expected {total_rows} rows, "
                    f"got {copied_rows}. Original table has been restored."
                )

        # Step 4: Drop the old (frozen) table.
        self.execute(self.sql_delete_table % {"table": q_old})

        # Step 5: Rename the new table to the original name.
        # alter_db_table also updates deferred SQL references from
        # new__<table> to the original table name.
        self.alter_db_table(new_model, new_table, original_table)

        # Step 6: Run deferred SQL (indexes) on the correctly-named table.
        # Each execute() auto-commits (can_rollback_ddl = False), so each
        # CREATE INDEX ASYNC runs in its own transaction as DSQL requires.
        # Only flush SQL added by create_model for this table; preserve
        # deferred SQL from other tables queued earlier in the session.
        remake_deferred = self.deferred_sql[pre_deferred_count:]
        self.deferred_sql = self.deferred_sql[:pre_deferred_count]
        for sql in remake_deferred:
            self.execute(sql)
        # Fix any PK-removed field
        if restore_pk_field:
            restore_pk_field.primary_key = True

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

        Aurora DSQL's ADD COLUMN only supports 'column_name data_type' -- no
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
        # M2M fields are a special case -- just drop the through table.
        if field.many_to_many:
            if field.remote_field.through._meta.auto_created:
                self.delete_model(field.remote_field.through)
            return
        # It might not actually have a column behind it
        if field.db_parameters(connection=self.connection)["type"] is None:
            return
        self._remake_table(model, delete_field=field)
