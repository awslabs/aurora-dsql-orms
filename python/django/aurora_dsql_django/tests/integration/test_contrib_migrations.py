# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Integration test for Django contrib app migrations.

Runs the full migration sequence for auth, contenttypes, admin, and sessions
against a real DSQL cluster. These migrations exercise ALTER COLUMN, DROP COLUMN,
and ADD COLUMN operations that require the adapter's table recreation support.
"""

import time
import unittest

from django.core.management import call_command
from django.db import connection, OperationalError


def _drop_tables_with_retry(tables, max_retries=3, delay=1.0):
    """
    Drop tables one by one, retrying on DSQL OCC errors.

    DSQL may return SerializationFailure (OC000/OC001) when schema changes
    conflict. Each DROP is retried independently with a fresh connection.
    """
    for table in tables:
        for attempt in range(max_retries):
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"DROP TABLE IF EXISTS {connection.ops.quote_name(table)}"
                    )
                break
            except OperationalError:
                if attempt == max_retries - 1:
                    break  # Best-effort cleanup -- don't fail teardown
                connection.close()
                time.sleep(delay)


# All tables that Django contrib migrations create, in dependency order.
_DJANGO_TABLES = [
    "django_admin_log",
    "auth_user_user_permissions",
    "auth_user_groups",
    "auth_permission",
    "auth_group_permissions",
    "auth_group",
    "auth_user",
    "django_content_type",
    "django_session",
    "django_migrations",
]


class TestContribMigrations(unittest.TestCase):
    """
    Run Django's contrib migrations against a real DSQL cluster.

    Verifies that all default Django contrib app migrations complete
    successfully and produce the expected schema.
    """

    @classmethod
    def setUpClass(cls):
        """Drop all Django tables to start from a clean state."""
        super().setUpClass()
        connection.close()
        _drop_tables_with_retry(_DJANGO_TABLES)
        # Let schema changes propagate before running migrations.
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        """Clean up all tables created by migrations."""
        connection.close()
        _drop_tables_with_retry(_DJANGO_TABLES)
        super().tearDownClass()

    def test_migrate_contenttypes_and_auth(self):
        """
        Run all contenttypes and auth migrations and verify the final schema.

        Key operations covered:
          - contenttypes.0002: AlterField (nullability) + RemoveField
          - auth.0002-0012: AlterField (varchar length, nullability changes)
        """
        # Run migrate -- this will apply all migrations for INSTALLED_APPS.
        # DSQL may throw OCC errors (OC000/OC001) if schema changes haven't
        # fully propagated. Retry with a fresh connection.
        last_error = None
        for attempt in range(3):
            try:
                connection.close()
                call_command("migrate", verbosity=1, no_color=True)
                last_error = None
                break
            except OperationalError as e:
                last_error = e
                if attempt < 2:
                    connection.close()
                    # Clean up partial migration state before retrying.
                    _drop_tables_with_retry(_DJANGO_TABLES)
                    time.sleep(3)
                    continue
                break
            except Exception as e:
                last_error = e
                break
        if last_error is not None:
            self.fail(f"Django migrate failed: {last_error}")

        # Verify the key tables exist with the correct final schema
        with connection.cursor() as cursor:
            # django_content_type should exist WITHOUT the 'name' column
            # (contenttypes.0002 removes it via AlterField + RemoveField)
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'django_content_type' "
                "ORDER BY ordinal_position"
            )
            ct_columns = [row[0] for row in cursor.fetchall()]
            self.assertIn("id", ct_columns)
            self.assertIn("app_label", ct_columns)
            self.assertIn("model", ct_columns)
            self.assertNotIn("name", ct_columns, "contenttypes.0002 should remove the 'name' column")

            # auth_user should exist with the final column sizes
            # (auth.0008 changes username max_length 30->150, etc.)
            cursor.execute(
                "SELECT column_name, character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_name = 'auth_user' AND column_name = 'username'"
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row, "auth_user.username column should exist")
            self.assertEqual(row[1], 150, "username max_length should be 150 after auth.0008")

            # auth_user.last_login should be nullable
            # (auth.0005 changes it from NOT NULL to NULL)
            cursor.execute(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'auth_user' AND column_name = 'last_login'"
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row, "auth_user.last_login column should exist")
            self.assertEqual(row[0], "YES", "last_login should be nullable after auth.0005")

            # auth_permission.name should have max_length 255
            # (auth.0002 changes it from 50->255)
            cursor.execute(
                "SELECT character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_name = 'auth_permission' AND column_name = 'name'"
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row, "auth_permission.name column should exist")
            self.assertEqual(row[0], 255, "permission name max_length should be 255 after auth.0002")

        # Verify migrations are recorded
        with connection.cursor() as cursor:
            cursor.execute("SELECT app, name FROM django_migrations WHERE app IN ('contenttypes', 'auth') ORDER BY app, name")
            applied = {(row[0], row[1]) for row in cursor.fetchall()}

            # The critical migrations that previously failed
            self.assertIn(("contenttypes", "0002_remove_content_type_name"), applied)
            self.assertIn(("auth", "0002_alter_permission_name_max_length"), applied)
            self.assertIn(("auth", "0005_alter_user_last_login_null"), applied)
            self.assertIn(("auth", "0008_alter_user_username_max_length"), applied)
