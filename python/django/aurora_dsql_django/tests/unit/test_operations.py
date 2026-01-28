# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import MagicMock

import django
from django.conf import settings

# Required before importing DatabaseOperations.
if not settings.configured:
    settings.configure()
    django.setup()

from aurora_dsql_django.operations import DatabaseOperations


class TestDatabaseOperations(unittest.TestCase):
    def setUp(self):
        mock_connection = MagicMock()
        self.ops = DatabaseOperations(mock_connection)

    def test_cast_data_types(self):
        expected_cast_data_types = {
            "AutoField": "uuid",
            "BigAutoField": "uuid",
            "SmallAutoField": "smallint",
        }
        self.assertEqual(self.ops.cast_data_types, expected_cast_data_types)

    def test_deferrable_sql(self):
        self.assertEqual(self.ops.deferrable_sql(), "")

    def test_deferrable_sql_no_arguments(self):
        # Ensure the method doesn't accept any arguments
        with self.assertRaises(TypeError):
            self.ops.deferrable_sql(True)

    def test_inheritance(self):
        from django.db.backends.postgresql.operations import DatabaseOperations as PostgreSQLDatabaseOperations

        self.assertIsInstance(self.ops, PostgreSQLDatabaseOperations)

    def test_overridden_attributes(self):
        from django.db.backends.postgresql.operations import DatabaseOperations as PostgreSQLDatabaseOperations

        postgresql_ops = PostgreSQLDatabaseOperations(None)

        # Check that we've actually overridden some attributes
        self.assertNotEqual(self.ops.cast_data_types, postgresql_ops.cast_data_types)

    def test_cast_data_types_autofield(self):
        self.assertEqual(self.ops.cast_data_types["AutoField"], "uuid")

    def test_cast_data_types_bigautofield(self):
        self.assertEqual(self.ops.cast_data_types["BigAutoField"], "uuid")

    def test_cast_data_types_smallautofield(self):
        self.assertEqual(self.ops.cast_data_types["SmallAutoField"], "smallint")

    def test_integer_field_range_for_uuid(self):
        """Test that UUIDField returns None for integer field range."""
        result = self.ops.integer_field_range("UUIDField")
        self.assertEqual(result, (None, None))

    def test_integer_field_range_for_integer_field(self):
        """Test that IntegerField returns normal integer ranges."""
        result = self.ops.integer_field_range("IntegerField")
        self.assertIsNotNone(result[0], "No min provided")
        self.assertIsNotNone(result[1], "No max provided")
        self.assertTrue(result[0] <= result[1], "min > max")

    def test_integer_field_range_for_big_integer_field(self):
        """Test that BigIntegerField returns normal integer ranges."""
        result = self.ops.integer_field_range("BigIntegerField")
        self.assertIsNotNone(result[0], "No min provided")
        self.assertIsNotNone(result[1], "No max provided")
        self.assertTrue(result[0] <= result[1], "min > max")


if __name__ == "__main__":
    unittest.main()
