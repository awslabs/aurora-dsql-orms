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

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor._check_sql")
    def test_check_sql_feature_disabled(self, mock_super_check_sql):
        self.connection.features.supports_table_check_constraints = False

        result = self.schema_editor._check_sql("test_check", "age >= 0")

        self.assertIsNone(result)
        mock_super_check_sql.assert_not_called()

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor._check_sql")
    def test_check_sql_feature_enabled(self, mock_super_check_sql):
        self.connection.features.supports_table_check_constraints = True
        mock_super_check_sql.return_value = "CHECK (age >= 0)"

        result = self.schema_editor._check_sql("test_check", "age >= 0")

        mock_super_check_sql.assert_called_once_with("test_check", "age >= 0")
        self.assertEqual(result, "CHECK (age >= 0)")

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.add_constraint")
    def test_add_constraint_check_disabled(self, mock_super_add_constraint):
        model = MagicMock()
        constraint = create_check_constraint(Q(age__gte=0), "age_check")
        self.connection.features.supports_table_check_constraints = False

        result = self.schema_editor.add_constraint(model, constraint)

        self.assertIsNone(result)
        mock_super_add_constraint.assert_not_called()

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.add_constraint")
    def test_add_constraint_check_enabled(self, mock_super_add_constraint):
        model = MagicMock()
        constraint = create_check_constraint(Q(age__gte=0), "age_check")
        self.connection.features.supports_table_check_constraints = True

        self.schema_editor.add_constraint(model, constraint)

        mock_super_add_constraint.assert_called_once_with(model, constraint)

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.add_constraint")
    def test_add_constraint_non_check(self, mock_super_add_constraint):
        model = MagicMock()
        constraint = UniqueConstraint(fields=["name"], name="unique_name")
        self.connection.features.supports_table_check_constraints = False

        self.schema_editor.add_constraint(model, constraint)

        mock_super_add_constraint.assert_called_once_with(model, constraint)

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.remove_constraint")
    def test_remove_constraint_check_disabled(self, mock_super_remove_constraint):
        model = MagicMock()
        constraint = create_check_constraint(Q(age__gte=0), "age_check")
        self.connection.features.supports_table_check_constraints = False

        result = self.schema_editor.remove_constraint(model, constraint)

        self.assertIsNone(result)
        mock_super_remove_constraint.assert_not_called()

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.remove_constraint")
    def test_remove_constraint_check_enabled(self, mock_super_remove_constraint):
        model = MagicMock()
        constraint = create_check_constraint(Q(age__gte=0), "age_check")
        self.connection.features.supports_table_check_constraints = True

        self.schema_editor.remove_constraint(model, constraint)

        mock_super_remove_constraint.assert_called_once_with(model, constraint)

    @patch("aurora_dsql_django.schema.schema.DatabaseSchemaEditor.remove_constraint")
    def test_remove_constraint_non_check(self, mock_super_remove_constraint):
        model = MagicMock()
        constraint = UniqueConstraint(fields=["name"], name="unique_name")
        self.connection.features.supports_table_check_constraints = False

        self.schema_editor.remove_constraint(model, constraint)

        mock_super_remove_constraint.assert_called_once_with(model, constraint)


if __name__ == "__main__":
    unittest.main()
