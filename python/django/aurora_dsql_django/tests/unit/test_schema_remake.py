# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for _remake_table recovery logic and row count verification.

These tests mock the database layer to verify that the recovery and
verification paths in _remake_table behave correctly without requiring
a real DSQL cluster.
"""

import unittest
from unittest.mock import MagicMock, patch

import django
from django.conf import settings
from django.db import models

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "aurora_dsql_django"}},
        INSTALLED_APPS=["django.contrib.contenttypes"],
    )
    django.setup()

from aurora_dsql_django.schema import DatabaseSchemaEditor


def _make_model(table_name="test_table"):
    """Create a minimal dynamic model for _remake_table tests."""
    meta = type(
        "Meta",
        (),
        {
            "app_label": "contenttypes",
            "db_table": table_name,
        },
    )
    return type(
        "TestModel",
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

        execute_calls = [str(c) for c in mock_execute.call_args_list]
        # Should DROP new__ (if exists) then RENAME old__ → original.
        drop_new = any("DROP" in c and "new__" in c for c in execute_calls)
        rename_old = any("RENAME" in c and "old__" in c for c in execute_calls)
        self.assertTrue(drop_new, f"Expected DROP new__ in recovery, got: {execute_calls}")
        self.assertTrue(rename_old, f"Expected RENAME old__ back in recovery, got: {execute_calls}")

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

        execute_calls = [str(c) for c in mock_execute.call_args_list]
        rename_new = any("RENAME" in c and "new__" in c for c in execute_calls)
        self.assertTrue(rename_new, f"Expected RENAME new__ back in recovery, got: {execute_calls}")

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

    @patch.object(DatabaseSchemaEditor, "alter_db_table")
    @patch.object(DatabaseSchemaEditor, "create_model")
    @patch.object(DatabaseSchemaEditor, "execute")
    @patch.object(DatabaseSchemaEditor, "_query_with_retry")
    @patch.object(DatabaseSchemaEditor, "_table_exists")
    def test_cleanup_leftover_temp_tables(self, mock_exists, mock_query, mock_execute, mock_create, mock_alter):
        """When original exists with leftover old__/new__, clean them up."""
        mock_exists.side_effect = _table_exists_factory(original=True, old=True, new=True)
        mock_query.return_value = [(0,)]

        Model = _make_model()
        old_field = Model._meta.get_field("name")
        new_field = Model._meta.get_field("name")
        self.editor._remake_table(Model, alter_fields=[(old_field, new_field)])

        execute_calls = [str(c) for c in mock_execute.call_args_list]
        drop_old = any("DROP" in c and "old__" in c for c in execute_calls)
        drop_new = any("DROP" in c and "new__" in c for c in execute_calls)
        self.assertTrue(drop_old, f"Expected DROP old__ cleanup, got: {execute_calls}")
        self.assertTrue(drop_new, f"Expected DROP new__ cleanup, got: {execute_calls}")


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

        # Verify it tried to restore: DROP new__ + RENAME old__ → original.
        execute_calls = [str(c) for c in mock_execute.call_args_list]
        drop_new = any("DROP" in c and "new__" in c for c in execute_calls)
        rename_back = any("RENAME" in c and "old__" in c for c in execute_calls)
        self.assertTrue(drop_new, f"Expected DROP new__ on verification failure, got: {execute_calls}")
        self.assertTrue(rename_back, f"Expected RENAME old__ back on verification failure, got: {execute_calls}")

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

        # Should not have any INSERT calls.
        execute_calls = [str(c) for c in mock_execute.call_args_list]
        inserts = [c for c in execute_calls if "INSERT" in c]
        self.assertEqual(len(inserts), 0, f"Expected no INSERT for empty table, got: {execute_calls}")


if __name__ == "__main__":
    unittest.main()
