# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest

from aurora_dsql_django.features import DatabaseFeatures


class TestDatabaseFeatures(unittest.TestCase):
    def setUp(self):
        # DatabaseFeatures usually requires a connection object, but for these tests,
        # we can pass None as we're only checking static attributes
        self.features = DatabaseFeatures(None)

    def test_can_rollback_ddl(self):
        self.assertFalse(self.features.can_rollback_ddl)

    def test_supports_forward_references(self):
        self.assertTrue(self.features.supports_forward_references)

    def test_supports_foreign_keys(self):
        self.assertFalse(self.features.supports_foreign_keys)

    def test_supports_check_constraints(self):
        self.assertFalse(self.features.supports_table_check_constraints)

    def test_can_create_inline_fk(self):
        self.assertFalse(self.features.can_create_inline_fk)

    def test_can_clone_databases(self):
        self.assertFalse(self.features.can_clone_databases)

    def test_can_defer_constraint_checks(self):
        self.assertFalse(self.features.can_defer_constraint_checks)

    def test_supports_deferrable_unique_constraints(self):
        self.assertFalse(self.features.supports_deferrable_unique_constraints)

    def test_has_native_json_field(self):
        self.assertFalse(self.features.has_native_json_field)

    def test_can_introspect_materialized_views(self):
        self.assertFalse(self.features.can_introspect_materialized_views)

    def test_uses_savepoints(self):
        self.assertFalse(self.features.uses_savepoints)

    def test_can_release_savepoints(self):
        self.assertFalse(self.features.can_release_savepoints)

    def test_can_rename_index(self):
        self.assertTrue(self.features.can_rename_index)

    def test_supports_expression_indexes(self):
        self.assertFalse(self.features.supports_expression_indexes)

    def test_inheritance(self):
        from django.db.backends.postgresql.features import DatabaseFeatures as PostgreSQLDatabaseFeatures

        self.assertIsInstance(self.features, PostgreSQLDatabaseFeatures)

    def test_overridden_attributes(self):
        from django.db.backends.postgresql.features import DatabaseFeatures as PostgreSQLDatabaseFeatures

        postgresql_features = PostgreSQLDatabaseFeatures(None)

        # Check that we've actually overridden some attributes
        self.assertNotEqual(self.features.can_rollback_ddl, postgresql_features.can_rollback_ddl)
        self.assertNotEqual(self.features.supports_foreign_keys, postgresql_features.supports_foreign_keys)
        self.assertNotEqual(self.features.can_clone_databases, postgresql_features.can_clone_databases)
        self.assertNotEqual(self.features.has_native_json_field, postgresql_features.has_native_json_field)


if __name__ == "__main__":
    unittest.main()
