import unittest
from unittest.mock import MagicMock, patch
import django
from django.conf import settings
from django.db import models
from aurora_dsql_django.base import DatabaseWrapper
from aurora_dsql_django.features import DatabaseFeatures
from aurora_dsql_django.schema import DatabaseSchemaEditor

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=['django.contrib.contenttypes'],
        DATABASES={'default': {'ENGINE': 'aurora_dsql_django'}},
        USE_TZ=True,
    )
    django.setup()


class TestWrapper(unittest.TestCase):
    """Test Aurora DSQL wrapper behavior when all parts are working together"""

    def setUp(self):
        self.connection = DatabaseWrapper({})
        self.connection.connection = MagicMock()
        self.connection.connection.encoding = 'utf8'

        # Configure mock to use real components.
        self.connection.features = DatabaseFeatures(self.connection)
        self.schema_editor = DatabaseSchemaEditor(self.connection)

    def test_foreign_key_sql_generation(self):
        """Ensure foreign key SQL is not generated when the feature is disabled"""

        class ParentModel(models.Model):
            class Meta:
                app_label = 'test_app'

        class ChildModel(models.Model):
            parent = models.ForeignKey(ParentModel, on_delete=models.CASCADE)

            class Meta:
                app_label = 'test_app'

        # Mock execute to capture SQL without actually running it.
        with patch.object(self.schema_editor, 'execute'):
            with self.schema_editor:
                self.schema_editor.create_model(ChildModel)

                # Check that no foreign key SQL was deferred.
                foreign_key_statements = [sql for sql in self.schema_editor.deferred_sql if 'FOREIGN KEY' in str(sql)]
                self.assertListEqual([], foreign_key_statements, "Should not generate foreign key SQL")


if __name__ == '__main__':
    unittest.main()
