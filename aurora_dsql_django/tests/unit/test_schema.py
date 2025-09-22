import unittest
from unittest.mock import patch, MagicMock
from aurora_dsql_django.schema import DatabaseSchemaEditor
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


class TestDatabaseSchemaEditor(unittest.TestCase):

    def setUp(self):
        self.connection = MagicMock()
        self.schema_editor = DatabaseSchemaEditor(self.connection)

    def test_sql_attributes(self):
        self.assertEqual(self.schema_editor.sql_delete_fk, "")
        self.assertEqual(self.schema_editor.sql_create_pk, "")
        self.assertEqual(self.schema_editor.sql_create_index,
                         "CREATE INDEX ASYNC %(name)s ON %(table)s%(using)s (%(columns)s)%(include)s%(extra)s%(condition)s")
        self.assertEqual(self.schema_editor.sql_create_unique,
                         "CREATE UNIQUE INDEX ASYNC %(name)s ON %(table)s (%(columns)s)")
        self.assertEqual(
            self.schema_editor.sql_delete_unique,
            "DROP INDEX %(name)s CASCADE")
        self.assertEqual(
            self.schema_editor.sql_update_with_default,
            "UPDATE %(table)s SET %(column)s = %(default)s WHERE %(column)s IS NULL"
        )
        self.assertEqual(self.schema_editor.sql_create_fk, "")
        self.assertEqual(self.schema_editor.sql_create_check, "")
        self.assertEqual(self.schema_editor.sql_delete_check, "")
        self.assertEqual(self.schema_editor.sql_delete_constraint, "")
        self.assertEqual(self.schema_editor.sql_delete_column, "")

    @patch('aurora_dsql_django.schema.schema.DatabaseSchemaEditor.add_index')
    def test_add_index_with_expressions(self, mock_super_add_index):
        model = MagicMock()
        index = MagicMock(contains_expressions=True)
        self.connection.features.supports_expression_indexes = False

        result = self.schema_editor.add_index(model, index)

        self.assertIsNone(result)
        mock_super_add_index.assert_not_called()

    @patch('aurora_dsql_django.schema.schema.DatabaseSchemaEditor.add_index')
    def test_add_index_without_expressions(self, mock_super_add_index):
        model = MagicMock()
        index = MagicMock(contains_expressions=False)

        self.schema_editor.add_index(model, index)

        mock_super_add_index.assert_called_once_with(model, index, False)

    @patch('aurora_dsql_django.schema.schema.DatabaseSchemaEditor.remove_index')
    def test_remove_index_with_expressions(self, mock_super_remove_index):
        model = MagicMock()
        index = MagicMock(contains_expressions=True)
        self.connection.features.supports_expression_indexes = False

        result = self.schema_editor.remove_index(model, index)

        self.assertIsNone(result)
        mock_super_remove_index.assert_not_called()

    @patch('aurora_dsql_django.schema.schema.DatabaseSchemaEditor.remove_index')
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

        result = self.schema_editor._index_columns(
            table, columns, col_suffixes, opclasses)

        expected = BaseDatabaseSchemaEditor._index_columns(
            self.schema_editor, table, columns, col_suffixes, opclasses
        )

        self.assertIsInstance(result, type(expected))
        self.assertEqual(result.table, expected.table)
        self.assertEqual(result.columns, expected.columns)

    def test_create_like_index_sql(self):
        model = MagicMock()
        field = MagicMock()

        result = self.schema_editor._create_like_index_sql(model, field)

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
