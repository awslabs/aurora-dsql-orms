# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from django.db import connections, transaction
from django.test import TestCase


class TestAuroraDSQLAdapter(TestCase):
    databases = {"default"}

    @classmethod
    def setUpClass(cls):
        cls.connection = connections["default"]
        transaction.set_autocommit(False)
        super().setUpClass()

    def setUp(self):
        self.connection.needs_rollback = False
        # Disable Django's transaction management for this test case
        self.connection.disable_constraint_checking()
        self.connection.features.can_rollback_ddl = False

    def test_connection_params(self):
        params = self.connection.get_connection_params()

        self.assertEqual(params["host"], os.environ.get("CLUSTER_ENDPOINT", None))
        self.assertEqual(params["user"], "admin")
        # Password is set by the connector during connect(), not in get_connection_params()
        self.assertEqual(params["application_name"], "django")

        # Test database connection
        with self.connection.cursor() as cursor:
            cursor.execute("BEGIN")
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.execute("COMMIT")
            self.assertEqual(result[0], 1)

    def test_application_name_set(self):
        """Test that application_name is properly set for tracking."""
        params = self.connection.get_connection_params()
        self.assertEqual(params["application_name"], "django")

    def test_table_creation(self):
        with self.connection.cursor() as cursor:
            try:
                # Start a new transaction
                cursor.execute("BEGIN")

                # Create table
                cursor.execute("CREATE TABLE foobar (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT)")

                # Verify index creation
                cursor.execute("SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'foobar'")
                count = cursor.fetchone()[0]
                self.assertEqual(count, 1)

                # Complete the transaction
                cursor.execute("COMMIT")

                # Start a new transaction
                cursor.execute("BEGIN")

                # Delete the table
                cursor.execute("DROP TABLE IF EXISTS foobar")

                # Verify index destruction
                cursor.execute("SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'foobar'")
                count = cursor.fetchone()[0]
                self.assertEqual(count, 0)

                # Complete the transaction
                cursor.execute("COMMIT")

            except Exception as e:
                # If an error occurs, rollback the transaction
                cursor.execute("ROLLBACK")
                raise e

            finally:
                # Verify that the table has been deleted
                cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'test_index'")
                count = cursor.fetchone()[0]
                self.assertEqual(count, 0)
