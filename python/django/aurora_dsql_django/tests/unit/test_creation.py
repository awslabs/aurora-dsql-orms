# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import MagicMock, patch

from aurora_dsql_django.creation import DatabaseCreation


class TestDatabaseCreation(unittest.TestCase):
    def setUp(self):
        # Create a mock connection object
        self.mock_connection = MagicMock()
        self.creation = DatabaseCreation(self.mock_connection)

    def test_clone_test_db_raises_not_implemented_error(self):
        with self.assertRaises(NotImplementedError) as context:
            self.creation._clone_test_db(suffix="test", verbosity=1)

        self.assertIn("Aurora DSQL doesn't support cloning databases", str(context.exception))
        self.assertIn("Disable the option to run tests in parallel processes", str(context.exception))

    """
    The 'keepdb' parameter in Django's test database creation process determines whether
    to keep the test database after the tests are run or to destroy it.

    - When keepdb=False (default): Django creates a new test database for each test run
      and destroys it after the tests complete. This ensures a clean state for each test run
      but can be time-consuming for large databases.

    - When keepdb=True: Django tries to reuse the existing test database if it exists,
      instead of creating a new one. This can significantly speed up the test process,
      especially for large databases, but may retain data from previous test runs.

    In the context of Aurora DSQL, both options raise NotImplementedError because
    database cloning is not supported.

    For more information on keepdb, see Django's documentation:
    https://docs.djangoproject.com/en/stable/ref/django-admin/#cmdoption-test-keepdb
    """

    def test_clone_test_db_with_keepdb(self):
        with self.assertRaises(NotImplementedError):
            self.creation._clone_test_db(suffix="test", verbosity=1, keepdb=True)

    @patch("aurora_dsql_django.creation.creation.DatabaseCreation._clone_test_db")
    def test_parent_clone_test_db_not_called(self, mock_parent_clone):
        with self.assertRaises(NotImplementedError):
            self.creation._clone_test_db(suffix="test", verbosity=1)

        mock_parent_clone.assert_not_called()

    def test_inheritance(self):
        from django.db.backends.postgresql.creation import DatabaseCreation as PostgreSQLDatabaseCreation

        self.assertIsInstance(self.creation, PostgreSQLDatabaseCreation)


if __name__ == "__main__":
    unittest.main()
