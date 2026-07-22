# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import MagicMock, patch

from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models.constraints import UniqueConstraint
from django.db.models.query_utils import Q

from aurora_dsql_django.schema import DatabaseSchemaEditor
from aurora_dsql_django.tests.utils import create_check_constraint


class TestDatabaseSchemaEditor(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.schema_editor = DatabaseSchemaEditor(self.connection)

    def test_sql_attributes(self):
        self.assertEqual(
            self.schema_editor.sql_create_index,
            "CREATE INDEX ASYNC %(name)s ON %(table)s%(using)s (%(columns)s)%(include)s%(extra)s%(condition)s",
        )
        self.assertEqual(self.schema_editor.sql_create_unique, "CREATE UNIQUE INDEX ASYNC %(name)s ON %(table)s (%(columns)s)")
        self.assertEqual(self.schema_editor.sql_delete_unique, "DROP INDEX %(name)s CASCADE")
        self.assertEqual(
            self.schema_editor.sql_update_with_default,
            "UPDATE %(table)s SET %(column)s = %(default)s WHERE %(column)s IS NULL",
        )

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.add_index")
    def test_add_index_with_expressions(self, mock_super_add_index):
        model = MagicMock()
        index = MagicMock(contains_expressions=True)
        self.connection.features.supports_expression_indexes = False

        result = self.schema_editor.add_index(model, index)

        self.assertIsNone(result)
        mock_super_add_index.assert_not_called()

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.add_index")
    def test_add_index_without_expressions(self, mock_super_add_index):
        model = MagicMock()
        index = MagicMock(contains_expressions=False)

        self.schema_editor.add_index(model, index)

        mock_super_add_index.assert_called_once_with(model, index, False)

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.remove_index")
    def test_remove_index_with_expressions(self, mock_super_remove_index):
        model = MagicMock()
        index = MagicMock(contains_expressions=True)
        self.connection.features.supports_expression_indexes = False

        result = self.schema_editor.remove_index(model, index)

        self.assertIsNone(result)
        mock_super_remove_index.assert_not_called()

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.remove_index")
    def test_remove_index_without_expressions(self, mock_super_remove_index):
        model = MagicMock()
        index = MagicMock(contains_expressions=False)

        self.schema_editor.remove_index(model, index)

        mock_super_remove_index.assert_called_once_with(model, index, False)

    def test_index_columns(self):
        table = "test_table"
        columns = ["col1", "col2"]
        col_suffixes = ["", ""]
        opclasses = ["", ""]

        result = self.schema_editor._index_columns(table, columns, col_suffixes, opclasses)

        expected = BaseDatabaseSchemaEditor._index_columns(self.schema_editor, table, columns, col_suffixes, opclasses)

        self.assertIsInstance(result, type(expected))
        self.assertEqual(result.table, expected.table)
        self.assertEqual(result.columns, expected.columns)

    def test_create_like_index_sql(self):
        model = MagicMock()
        field = MagicMock()

        result = self.schema_editor._create_like_index_sql(model, field)

        self.assertIsNone(result)

    def test_sql_create_check_uses_not_valid(self):
        # DSQL requires CHECK constraints on existing tables to be added
        # NOT VALID, then validated asynchronously.
        self.assertEqual(
            self.schema_editor.sql_create_check,
            "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s CHECK (%(check)s) NOT VALID",
        )
        self.assertEqual(
            self.schema_editor.sql_validate_check,
            "ALTER TABLE ASYNC %(table)s VALIDATE CONSTRAINT %(name)s",
        )

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.add_constraint")
    def test_add_check_constraint_validates_async(self, mock_super_add_constraint):
        # Adding a CHECK constraint must delegate to super() (which emits the
        # NOT VALID ADD via sql_create_check) and then issue VALIDATE CONSTRAINT
        # ASYNC as a follow-up.
        model = MagicMock()
        model._meta.db_table = "my_table"
        self.schema_editor.quote_name = lambda n: f'"{n}"'
        self.schema_editor.execute = MagicMock()
        constraint = create_check_constraint(Q(age__gte=0), "age_check")

        self.schema_editor.add_constraint(model, constraint)

        mock_super_add_constraint.assert_called_once_with(model, constraint)
        self.schema_editor.execute.assert_called_once_with(
            'ALTER TABLE ASYNC "my_table" VALIDATE CONSTRAINT "age_check"'
        )

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.add_constraint")
    def test_add_non_check_constraint_no_validate(self, mock_super_add_constraint):
        # Non-CHECK constraints (e.g. UNIQUE) must not trigger a follow-up
        # VALIDATE CONSTRAINT statement.
        model = MagicMock()
        self.schema_editor.execute = MagicMock()
        constraint = UniqueConstraint(fields=["name"], name="unique_name")

        self.schema_editor.add_constraint(model, constraint)

        mock_super_add_constraint.assert_called_once_with(model, constraint)
        self.schema_editor.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
