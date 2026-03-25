# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for _remake_table recovery logic and row count verification.

These tests mock the database layer to verify that the recovery and
verification paths in _remake_table behave correctly without requiring
a real DSQL cluster.
"""

import itertools
import unittest
from unittest.mock import MagicMock, patch

import django
from django.conf import settings
from django.db import OperationalError, models

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "aurora_dsql_django"}},
        INSTALLED_APPS=["django.contrib.contenttypes"],
    )
    django.setup()

from aurora_dsql_django.schema import DatabaseSchemaEditor

# Counter for unique model names to avoid Django re-registration warnings.
_model_counter = itertools.count()


def _make_model(table_name="test_table"):
    """Create a minimal dynamic model for _remake_table tests."""
    n = next(_model_counter)
    meta = type(
        "Meta",
        (),
        {
            "app_label": "contenttypes",
            "db_table": table_name,
        },
    )
    return type(
        f"RemakeTestModel{n}",
        (models.Model,),
        {
            "__module__": "django.contrib.contenttypes.models",
            "Meta": meta,
            "name": models.CharField(max_length=100),
        },
    )


def _table_exists_factory(original=True, old=False, new=False):
    """Return a side_effect function for _table_exists based on table states."""

    def _side_effect(table_name):
        if "old__" in table_name:
            return old
        elif "new__" in table_name:
            return new
        return original

    return _side_effect


def _setup_editor():
    """Create a DatabaseSchemaEditor with a properly configured mock connection."""
    connection = MagicMock()
    connection.ops.quote_name.side_effect = lambda name: f'"{name}"'
    editor = DatabaseSchemaEditor(connection)
    editor.deferred_sql = []
    return editor


def _get_sql_strings(mock_execute):
    """Extract SQL strings from mock execute call_args_list."""
    return [str(c) for c in mock_execute.call_args_list]


class TestRemakeTableRecovery(unittest.TestCase):
    """Test _remake_table step 0: recovery from prior failed attempts."""

    def setUp(self):
        self.editor = _setup_editor()

    @patch.object(DatabaseSchemaEditor, "alter_db_table")
    @patch.object(DatabaseSchemaEditor, "create_model")
    @patch.object(DatabaseSchemaEditor, "execute")
    @patch.object(DatabaseSchemaEditor, "_query_with_retry")
    @patch.object(DatabaseSchemaEditor, "_table_exists")
    def test_recovery_from_old_table(self, mock_exists, mock_query, mock_execute, mock_create, mock_alter):
        """When only old__ exists (failed after rename), recover by renaming old__ back."""
        mock_exists.side_effect = _table_exists_factory(original=False, old=True, new=False)
        mock_query.return_value = [(0,)]

        Model = _make_model()
        old_field = Model._meta.get_field("name")
        new_field = Model._meta.get_field("name")
        self.editor._remake_table(Model, alter_fields=[(old_field, new_field)])

        calls = _get_sql_strings(mock_execute)
        # First two calls should be the recovery: DROP new__ (cleanup) then RENAME old__ → original.
        self.assertGreaterEqual(len(calls), 2, f"Expected at least 2 execute calls, got: {calls}")
        self.assertIn("DROP", calls[0])
        self.assertIn("new__", calls[0])
        self.assertIn("RENAME", calls[1])
        self.assertIn("old__", calls[1])
        self.assertIn("test_table", calls[1])

    @patch.object(DatabaseSchemaEditor, "alter_db_table")
    @patch.object(DatabaseSchemaEditor, "create_model")
    @patch.object(DatabaseSchemaEditor, "execute")
    @patch.object(DatabaseSchemaEditor, "_query_with_retry")
    @patch.object(DatabaseSchemaEditor, "_table_exists")
    def test_recovery_from_new_table(self, mock_exists, mock_query, mock_execute, mock_create, mock_alter):
        """When only new__ exists (failed after DROP old__), recover by renaming new__ back."""
        mock_exists.side_effect = _table_exists_factory(original=False, old=False, new=True)
        mock_query.return_value = [(0,)]

        Model = _make_model()
        old_field = Model._meta.get_field("name")
        new_field = Model._meta.get_field("name")
        self.editor._remake_table(Model, alter_fields=[(old_field, new_field)])

        calls = _get_sql_strings(mock_execute)
        # First call should be recovery: RENAME new__ → original.
        self.assertGreaterEqual(len(calls), 1, f"Expected at least 1 execute call, got: {calls}")
        self.assertIn("RENAME", calls[0])
        self.assertIn("new__", calls[0])
        self.assertIn("test_table", calls[0])

    @patch.object(DatabaseSchemaEditor, "execute")
    @patch.object(DatabaseSchemaEditor, "_table_exists")
    def test_recovery_no_tables_raises(self, mock_exists, mock_execute):
        """When none of the three tables exist, raise RuntimeError."""
        mock_exists.side_effect = _table_exists_factory(original=False, old=False, new=False)

        Model = _make_model()
        old_field = Model._meta.get_field("name")
        new_field = Model._meta.get_field("name")
        with self.assertRaises(RuntimeError) as ctx:
            self.editor._remake_table(Model, alter_fields=[(old_field, new_field)])

        self.assertIn("Manual intervention required", str(ctx.exception))
        self.assertIn("test_table", str(ctx.exception))

    @patch.object(DatabaseSchemaEditor, "alter_db_table")
    @patch.object(DatabaseSchemaEditor, "create_model")
    @patch.object(DatabaseSchemaEditor, "execute")
    @patch.object(DatabaseSchemaEditor, "_query_with_retry")
    @patch.object(DatabaseSchemaEditor, "_table_exists")
    def test_cleanup_leftover_temp_tables(self, mock_exists, mock_query, mock_execute, mock_create, mock_alter):
        """When original exists with leftover old__/new__, clean them up before proceeding."""
        mock_exists.side_effect = _table_exists_factory(original=True, old=True, new=True)
        mock_query.return_value = [(0,)]

        Model = _make_model()
        old_field = Model._meta.get_field("name")
        new_field = Model._meta.get_field("name")
        self.editor._remake_table(Model, alter_fields=[(old_field, new_field)])

        calls = _get_sql_strings(mock_execute)
        # First two calls should be cleanup: DROP old__ then DROP new__.
        self.assertGreaterEqual(len(calls), 2, f"Expected at least 2 execute calls, got: {calls}")
        self.assertIn("DROP", calls[0])
        self.assertIn("old__", calls[0])
        self.assertIn("DROP", calls[1])
        self.assertIn("new__", calls[1])


class TestRemakeTableVerification(unittest.TestCase):
    """Test _remake_table row count verification after copy."""

    def setUp(self):
        self.editor = _setup_editor()

    @patch.object(DatabaseSchemaEditor, "alter_db_table")
    @patch.object(DatabaseSchemaEditor, "create_model")
    @patch.object(DatabaseSchemaEditor, "execute")
    @patch.object(DatabaseSchemaEditor, "_query_with_retry")
    @patch.object(DatabaseSchemaEditor, "_table_exists")
    def test_row_count_mismatch_raises_and_restores(self, mock_exists, mock_query, mock_execute, mock_create, mock_alter):
        """When copied row count doesn't match source, abort and restore original table."""
        mock_exists.return_value = True

        # _query_with_retry calls in order:
        # 1. COUNT(*) FROM old__ → 5 rows
        # 2. SELECT pk ... LIMIT 1 → seed pk
        # 3. SELECT pk ... OFFSET → no more rows (single batch)
        # 4. COUNT(*) FROM new__ → 3 rows (mismatch!)
        mock_query.side_effect = [
            [(5,)],  # total_rows
            [(1,)],  # seed pk
            [],  # no more batches
            [(3,)],  # copied_rows (mismatch)
        ]

        Model = _make_model()
        old_field = Model._meta.get_field("name")
        new_field = Model._meta.get_field("name")
        with self.assertRaises(RuntimeError) as ctx:
            self.editor._remake_table(Model, alter_fields=[(old_field, new_field)])

        error_msg = str(ctx.exception)
        self.assertIn("copy verification failed", error_msg)
        self.assertIn("expected 5", error_msg)
        self.assertIn("got 3", error_msg)
        self.assertIn("Original table has been restored", error_msg)

        # Last two execute calls before the exception should be the restore:
        # DROP new__ then RENAME old__ → original.
        calls = _get_sql_strings(mock_execute)
        self.assertIn("DROP", calls[-2])
        self.assertIn("new__", calls[-2])
        self.assertIn("RENAME", calls[-1])
        self.assertIn("old__", calls[-1])
        self.assertIn("test_table", calls[-1])

    @patch.object(DatabaseSchemaEditor, "alter_db_table")
    @patch.object(DatabaseSchemaEditor, "create_model")
    @patch.object(DatabaseSchemaEditor, "execute")
    @patch.object(DatabaseSchemaEditor, "_query_with_retry")
    @patch.object(DatabaseSchemaEditor, "_table_exists")
    def test_empty_table_skips_copy(self, mock_exists, mock_query, mock_execute, mock_create, mock_alter):
        """When source table has 0 rows, skip copy entirely."""
        mock_exists.return_value = True
        mock_query.return_value = [(0,)]

        Model = _make_model()
        old_field = Model._meta.get_field("name")
        new_field = Model._meta.get_field("name")
        self.editor._remake_table(Model, alter_fields=[(old_field, new_field)])

        calls = _get_sql_strings(mock_execute)
        inserts = [c for c in calls if "INSERT" in c]
        self.assertEqual(len(inserts), 0, f"Expected no INSERT for empty table, got: {calls}")

    @patch.object(DatabaseSchemaEditor, "alter_db_table")
    @patch.object(DatabaseSchemaEditor, "create_model")
    @patch.object(DatabaseSchemaEditor, "execute")
    @patch.object(DatabaseSchemaEditor, "_query_with_retry")
    @patch.object(DatabaseSchemaEditor, "_table_exists")
    def test_multi_batch_copy(self, mock_exists, mock_query, mock_execute, mock_create, mock_alter):
        """A table with 2500 rows requires 3 batches of 1000."""
        mock_exists.return_value = True

        # _query_with_retry calls in order:
        # 1. COUNT(*) FROM old__ → 2500
        # 2. SELECT pk ... LIMIT 1 → seed pk
        # 3. SELECT pk ... OFFSET → pk 1001 (next batch start)
        # 4. SELECT pk ... OFFSET → pk 2001 (next batch start)
        # 5. SELECT pk ... OFFSET → [] (no more rows)
        # 6. COUNT(*) FROM new__ → 2500 (verification passes)
        mock_query.side_effect = [
            [(2500,)],  # total_rows
            [(1,)],  # seed pk
            [(1001,)],  # next batch start
            [(2001,)],  # next batch start
            [],  # no more rows
            [(2500,)],  # copied_rows (matches)
        ]

        Model = _make_model()
        old_field = Model._meta.get_field("name")
        new_field = Model._meta.get_field("name")
        self.editor._remake_table(Model, alter_fields=[(old_field, new_field)])

        calls = _get_sql_strings(mock_execute)
        inserts = [c for c in calls if "INSERT" in c]
        self.assertEqual(len(inserts), 3, f"Expected 3 INSERT calls for 2500 rows, got: {inserts}")


def _make_occ_error(sqlstate="OC001"):
    """Create a mock OperationalError with a DSQL OCC sqlstate on __cause__."""
    cause = Exception()
    cause.sqlstate = sqlstate
    exc = OperationalError()
    exc.__cause__ = cause
    return exc


class TestOccRetry(unittest.TestCase):
    """Test _occ_retry behavior for OCC error handling."""

    def setUp(self):
        self.editor = _setup_editor()

    def test_occ_retry_succeeds_on_first_attempt(self):
        """fn() succeeds immediately, verify called once."""
        fn = MagicMock(return_value="ok")
        result = self.editor._occ_retry(fn)
        self.assertEqual(result, "ok")
        fn.assert_called_once()

    @patch("aurora_dsql_django.schema.time.sleep")
    def test_occ_retry_succeeds_after_retry(self, mock_sleep):
        """fn() raises OCC error on first call, succeeds on second."""
        fn = MagicMock(side_effect=[_make_occ_error("OC001"), "ok"])
        result = self.editor._occ_retry(fn)
        self.assertEqual(result, "ok")
        self.assertEqual(fn.call_count, 2)

    def test_occ_retry_raises_non_occ_error(self):
        """fn() raises a non-OCC OperationalError, verify it's raised immediately."""
        cause = Exception()
        cause.sqlstate = "42P01"  # Not an OCC error
        exc = OperationalError()
        exc.__cause__ = cause
        fn = MagicMock(side_effect=exc)
        with self.assertRaises(OperationalError):
            self.editor._occ_retry(fn)
        fn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
