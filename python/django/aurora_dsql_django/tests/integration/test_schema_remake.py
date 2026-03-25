# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for ALTER COLUMN and DROP COLUMN operations via table recreation.

Aurora DSQL does not support ALTER COLUMN (TYPE, SET/DROP NOT NULL) or DROP COLUMN.
The adapter handles these through a table recreation pattern. These tests verify
that pattern works correctly against a real DSQL cluster.
"""

import unittest

from django.db import connection, models


def _drop_table_if_exists(table_name):
    """Drop a table if it exists, ignoring errors."""
    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {connection.ops.quote_name(table_name)}")


class TestRemakeTableAlterField(unittest.TestCase):
    """Test _alter_field via table recreation on a real DSQL cluster."""

    def setUp(self):
        connection.close()
        _drop_table_if_exists("test_alter_field")

    def tearDown(self):
        connection.close()
        _drop_table_if_exists("test_alter_field")

    def _create_test_table(self, fields):
        """Create a test table using the schema editor."""
        meta = type(
            "Meta",
            (),
            {
                "app_label": "test",
                "db_table": "test_alter_field",
            },
        )
        attrs = {
            "__module__": "aurora_dsql_django.tests.integration",
            "Meta": meta,
        }
        attrs.update(fields)
        Model = type("TestAlterField", (models.Model,), attrs)

        with connection.schema_editor() as editor:
            editor.create_model(Model)
        return Model

    def _get_column_info(self, table_name, column_name):
        """Get column type and nullability from information_schema."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT data_type, character_maximum_length, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = %s",
                [table_name, column_name],
            )
            return cursor.fetchone()

    def _get_columns(self, table_name):
        """Get all column names for a table."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                [table_name],
            )
            return [row[0] for row in cursor.fetchall()]

    def test_alter_field_change_varchar_length(self):
        """Test that varchar max_length changes work via table recreation."""
        Model = self._create_test_table(
            {
                "name": models.CharField(max_length=50),
            }
        )

        old_field = models.CharField(max_length=50)
        old_field.set_attributes_from_name("name")
        old_field.model = Model

        new_field = models.CharField(max_length=255)
        new_field.set_attributes_from_name("name")
        new_field.model = Model

        with connection.schema_editor() as editor:
            editor.alter_field(Model, old_field, new_field)

        info = self._get_column_info("test_alter_field", "name")
        self.assertIsNotNone(info, "Column 'name' should exist after alter")
        self.assertEqual(info[1], 255)

    def test_alter_field_set_nullable(self):
        """Test that nullability changes work via table recreation."""
        Model = self._create_test_table(
            {
                "title": models.CharField(max_length=100),
            }
        )

        old_field = models.CharField(max_length=100)
        old_field.set_attributes_from_name("title")
        old_field.model = Model

        new_field = models.CharField(max_length=100, null=True)
        new_field.set_attributes_from_name("title")
        new_field.model = Model

        with connection.schema_editor() as editor:
            editor.alter_field(Model, old_field, new_field)

        info = self._get_column_info("test_alter_field", "title")
        self.assertIsNotNone(info, "Column 'title' should exist after alter")
        self.assertEqual(info[2], "YES")  # is_nullable

    def test_alter_field_preserves_data(self):
        """Test that existing row data survives a table recreation."""
        Model = self._create_test_table(
            {
                "name": models.CharField(max_length=50),
            }
        )

        # Insert test data
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO test_alter_field (name) VALUES (%s)",
                ["test_value"],
            )

        old_field = models.CharField(max_length=50)
        old_field.set_attributes_from_name("name")
        old_field.model = Model

        new_field = models.CharField(max_length=255)
        new_field.set_attributes_from_name("name")
        new_field.model = Model

        with connection.schema_editor() as editor:
            editor.alter_field(Model, old_field, new_field)

        # Verify data survived
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM test_alter_field")
            rows = cursor.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "test_value")


class TestRemakeTableRemoveField(unittest.TestCase):
    """Test remove_field via table recreation on a real DSQL cluster."""

    def setUp(self):
        connection.close()
        _drop_table_if_exists("test_remove_field")

    def tearDown(self):
        connection.close()
        _drop_table_if_exists("test_remove_field")

    def _create_test_table(self, fields):
        meta = type(
            "Meta",
            (),
            {
                "app_label": "test",
                "db_table": "test_remove_field",
            },
        )
        attrs = {
            "__module__": "aurora_dsql_django.tests.integration",
            "Meta": meta,
        }
        attrs.update(fields)
        Model = type("TestRemoveField", (models.Model,), attrs)

        with connection.schema_editor() as editor:
            editor.create_model(Model)
        return Model

    def _get_columns(self, table_name):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                [table_name],
            )
            return [row[0] for row in cursor.fetchall()]

    def test_remove_field(self):
        """Test that column removal works via table recreation."""
        Model = self._create_test_table(
            {
                "name": models.CharField(max_length=100, null=True),
                "code": models.CharField(max_length=50),
            }
        )

        field_to_remove = models.CharField(max_length=100, null=True)
        field_to_remove.set_attributes_from_name("name")
        field_to_remove.model = Model

        with connection.schema_editor() as editor:
            editor.remove_field(Model, field_to_remove)

        columns = self._get_columns("test_remove_field")
        self.assertNotIn("name", columns)
        self.assertIn("code", columns)
        self.assertIn("id", columns)

    def test_remove_field_preserves_data(self):
        """Test that remaining columns' data survives a column removal."""
        Model = self._create_test_table(
            {
                "name": models.CharField(max_length=100, null=True),
                "code": models.CharField(max_length=50),
            }
        )

        # Insert test data
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO test_remove_field (name, code) VALUES (%s, %s)",
                ["to_remove", "keep_this"],
            )

        field_to_remove = models.CharField(max_length=100, null=True)
        field_to_remove.set_attributes_from_name("name")
        field_to_remove.model = Model

        with connection.schema_editor() as editor:
            editor.remove_field(Model, field_to_remove)

        with connection.cursor() as cursor:
            cursor.execute("SELECT code FROM test_remove_field")
            rows = cursor.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "keep_this")


class TestRemakeTableAddField(unittest.TestCase):
    """Test add_field via table recreation on a real DSQL cluster."""

    def setUp(self):
        connection.close()
        _drop_table_if_exists("test_add_field")

    def tearDown(self):
        connection.close()
        _drop_table_if_exists("test_add_field")

    def _create_test_table(self, fields):
        meta = type(
            "Meta",
            (),
            {
                "app_label": "test",
                "db_table": "test_add_field",
            },
        )
        attrs = {
            "__module__": "aurora_dsql_django.tests.integration",
            "Meta": meta,
        }
        attrs.update(fields)
        Model = type("TestAddField", (models.Model,), attrs)

        with connection.schema_editor() as editor:
            editor.create_model(Model)
        return Model

    def _get_column_info(self, table_name, column_name):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT data_type, character_maximum_length, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = %s",
                [table_name, column_name],
            )
            return cursor.fetchone()

    def _get_columns(self, table_name):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                [table_name],
            )
            return [row[0] for row in cursor.fetchall()]

    def test_add_not_null_field_with_default(self):
        """Test adding a NOT NULL field with a default to an existing table.

        DSQL's ADD COLUMN only supports 'column_name data_type' -- no DEFAULT
        or NOT NULL inline. This must go through table recreation.
        """
        Model = self._create_test_table(
            {
                "name": models.CharField(max_length=100),
            }
        )

        # Insert a row before adding the field
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO test_add_field (name) VALUES (%s)",
                ["existing_row"],
            )

        new_field = models.CharField(max_length=50, default="pending")
        new_field.set_attributes_from_name("status")
        new_field.model = Model

        with connection.schema_editor() as editor:
            editor.add_field(Model, new_field)

        columns = self._get_columns("test_add_field")
        self.assertIn("status", columns)

        # Existing row should have the default value
        with connection.cursor() as cursor:
            cursor.execute("SELECT name, status FROM test_add_field")
            rows = cursor.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "existing_row")
            self.assertEqual(rows[0][1], "pending")

    def test_add_nullable_field(self):
        """Test adding a nullable field -- should use simple ADD COLUMN."""
        Model = self._create_test_table(
            {
                "name": models.CharField(max_length=100),
            }
        )

        new_field = models.CharField(max_length=200, null=True)
        new_field.set_attributes_from_name("description")
        new_field.model = Model

        with connection.schema_editor() as editor:
            editor.add_field(Model, new_field)

        info = self._get_column_info("test_add_field", "description")
        self.assertIsNotNone(info, "Column 'description' should exist")
        self.assertEqual(info[2], "YES")  # is_nullable
