# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import MagicMock, patch

import django
from django.conf import settings
from django.db import models
from django.db.models import Index, Q
from django.db.models.functions import Upper

from aurora_dsql_django.base import DatabaseWrapper
from aurora_dsql_django.features import DatabaseFeatures
from aurora_dsql_django.schema import DatabaseSchemaEditor
from aurora_dsql_django.tests.utils import create_check_constraint

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=["django.contrib.contenttypes"],
        DATABASES={"default": {"ENGINE": "aurora_dsql_django"}},
        USE_TZ=True,
    )
    django.setup()


def simple_quote_value(value):
    return f"'{value}'"


class TestWrapper(unittest.TestCase):
    """Test Aurora DSQL wrapper behavior when all parts are working together"""

    def setUp(self):
        self.connection = DatabaseWrapper({})
        self.connection.connection = MagicMock()

        # Configure mock to use real components.
        self.connection.features = DatabaseFeatures(self.connection)
        self.schema_editor = DatabaseSchemaEditor(self.connection)

    def _assert_sql_not_generated(self, operation_func, sql_patterns, message):
        """Helper method to verify SQL patterns are not generated"""
        executed_sql = []

        def mock_execute(sql, params=None):
            executed_sql.append((sql, params))

        # Capture SQL statements without running anything against a real DB.
        execute_patch = patch.object(self.schema_editor, "execute", side_effect=mock_execute)

        # Work around issue caused by missing encoding configuration in test environment.
        quote_patch = patch.object(self.schema_editor, "quote_value", side_effect=simple_quote_value)

        with execute_patch, quote_patch:
            with self.schema_editor:
                operation_func()

        all_sql = [str(sql) for sql, _ in executed_sql]
        if hasattr(self.schema_editor, "deferred_sql"):
            all_sql += [str(sql) for sql in self.schema_editor.deferred_sql]

        matching_statements = [sql for sql in all_sql if any(pattern in sql for pattern in sql_patterns)]
        self.assertListEqual([], matching_statements, message)

    def _capture_sql(self, operation_func):
        """Helper method to capture the SQL statements an operation generates"""
        executed_sql = []

        def mock_execute(sql, params=None):
            executed_sql.append((sql, params))

        # Capture SQL statements without running anything against a real DB.
        execute_patch = patch.object(self.schema_editor, "execute", side_effect=mock_execute)

        # Work around issue caused by missing encoding configuration in test environment.
        quote_patch = patch.object(self.schema_editor, "quote_value", side_effect=simple_quote_value)

        with execute_patch, quote_patch:
            with self.schema_editor:
                operation_func()

        all_sql = [str(sql) for sql, _ in executed_sql]
        if hasattr(self.schema_editor, "deferred_sql"):
            all_sql += [str(sql) for sql in self.schema_editor.deferred_sql]
        return all_sql

    def test_foreign_key_operations_ignored(self):
        """Ensure foreign key constraint operations are ignored for model creation when the feature is disabled"""

        class ParentModel(models.Model):
            class Meta:
                app_label = "test_app"

        class ChildModel(models.Model):
            parent = models.ForeignKey(ParentModel, on_delete=models.CASCADE)

            class Meta:
                app_label = "test_app"

        def operation():
            self.schema_editor.create_model(ChildModel)

        self._assert_sql_not_generated(operation, ["FOREIGN KEY", "REFERENCES"], "Should not generate foreign key SQL")

    def test_check_constraint_create_model_inline(self):
        """CHECK constraints are emitted inline in the CREATE TABLE statement"""

        class CheckConstraintModel(models.Model):
            age = models.IntegerField()

            class Meta:
                app_label = "test_app"
                constraints = [create_check_constraint(Q(age__gte=0), "age_gte_0")]

        def operation():
            self.schema_editor.create_model(CheckConstraintModel)

        all_sql = self._capture_sql(operation)
        create_table = [sql for sql in all_sql if sql.startswith("CREATE TABLE")]
        self.assertTrue(create_table, "Should generate a CREATE TABLE statement")
        self.assertTrue(
            any('CONSTRAINT "age_gte_0" CHECK' in sql for sql in create_table),
            f"CHECK constraint should be inline in CREATE TABLE: {create_table}",
        )

    def test_check_constraint_add_constraint_not_valid_then_validate(self):
        """add_constraint adds the CHECK as NOT VALID then validates it asynchronously"""

        class AddCheckConstraintModel(models.Model):
            age = models.IntegerField()

            class Meta:
                app_label = "test_app"

        constraint = create_check_constraint(Q(age__gte=0), "age_gte_0")

        def operation():
            self.schema_editor.add_constraint(AddCheckConstraintModel, constraint)

        all_sql = self._capture_sql(operation)
        self.assertTrue(
            any("ADD CONSTRAINT" in sql and "CHECK" in sql and "NOT VALID" in sql for sql in all_sql),
            f"Should add the CHECK constraint as NOT VALID: {all_sql}",
        )
        self.assertTrue(
            any("ALTER TABLE ASYNC" in sql and "VALIDATE CONSTRAINT" in sql for sql in all_sql),
            f"Should validate the constraint asynchronously: {all_sql}",
        )

    def test_check_constraint_remove_constraint_drops(self):
        """remove_constraint drops the CHECK constraint"""

        class RemoveCheckConstraintModel(models.Model):
            age = models.IntegerField()

            class Meta:
                app_label = "test_app"

        constraint = create_check_constraint(Q(age__gte=0), "age_gte_0")

        def operation():
            self.schema_editor.remove_constraint(RemoveCheckConstraintModel, constraint)

        all_sql = self._capture_sql(operation)
        self.assertTrue(
            any("DROP CONSTRAINT" in sql for sql in all_sql),
            f"Should drop the CHECK constraint: {all_sql}",
        )

    def test_remove_field_uses_native_drop_column(self):
        class RemoveFieldModel(models.Model):
            obsolete = models.CharField(max_length=100)

            class Meta:
                app_label = "test_app"
                db_table = "remove_field_test"

        def operation():
            self.schema_editor.remove_field(RemoveFieldModel, RemoveFieldModel._meta.get_field("obsolete"))

        self.assertEqual(
            self._capture_sql(operation),
            ['ALTER TABLE "remove_field_test" DROP COLUMN "obsolete" CASCADE'],
        )

    def test_add_index_expression_ignored(self):
        """Ensure add_index operations ignore expression indexes when the feature is disabled"""

        class AddIndexModel(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test_app"

        expression_index = Index(Upper("name"), name="upper_name_idx")

        def operation():
            self.schema_editor.add_index(AddIndexModel, expression_index)

        self._assert_sql_not_generated(
            operation, ["CREATE INDEX"], "Should not generate index creation SQL for expression indexes"
        )

    def test_remove_index_expression_ignored(self):
        """Ensure remove_index operations ignore expression indexes when the feature is disabled"""

        class RemoveIndexModel(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test_app"

        expression_index = Index(Upper("name"), name="upper_name_idx")

        def operation():
            self.schema_editor.remove_index(RemoveIndexModel, expression_index)

        self._assert_sql_not_generated(
            operation, ["DROP INDEX"], "Should not generate index removal SQL for expression indexes"
        )


if __name__ == "__main__":
    unittest.main()
