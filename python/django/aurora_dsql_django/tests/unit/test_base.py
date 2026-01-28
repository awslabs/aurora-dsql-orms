# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest
import uuid
from unittest.mock import MagicMock, patch

import django
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from aurora_dsql_django.base import DatabaseWrapper, _prepare_connection_params
from aurora_dsql_django.operations import DatabaseOperations

if not settings.configured:
    settings.configure(
        USE_I18N=True,
        DATABASES={"default": {"ENGINE": "aurora_dsql_django"}},
    )
    django.setup()


class TestPrepareConnectionParams(unittest.TestCase):
    """Tests for the _prepare_connection_params function."""

    def test_sets_application_name(self):
        params = {"host": "test-host", "user": "admin"}
        result = _prepare_connection_params(params)
        self.assertEqual(result["application_name"], "django")

    def test_sets_sslrootcert_for_verify_full(self):
        params = {"host": "test-host", "user": "admin", "sslmode": "verify-full"}
        result = _prepare_connection_params(params)
        self.assertEqual(result["sslrootcert"], "system")

    def test_preserves_custom_sslrootcert(self):
        params = {"host": "test-host", "user": "admin", "sslmode": "verify-full", "sslrootcert": "/path/to/cert.pem"}
        result = _prepare_connection_params(params)
        self.assertEqual(result["sslrootcert"], "/path/to/cert.pem")

    def test_no_sslrootcert_for_require_mode(self):
        params = {"host": "test-host", "user": "admin", "sslmode": "require"}
        result = _prepare_connection_params(params)
        self.assertNotIn("sslrootcert", result)

    def test_preserves_user(self):
        params = {"host": "test-host", "user": "admin"}
        result = _prepare_connection_params(params)
        self.assertEqual(result["user"], "admin")

    def test_preserves_profile(self):
        params = {"host": "test-host", "user": "admin", "profile": "my-profile"}
        result = _prepare_connection_params(params)
        self.assertEqual(result["profile"], "my-profile")

    def test_preserves_token_duration_secs(self):
        params = {"host": "test-host", "user": "admin", "token_duration_secs": 900}  # nosec B105
        result = _prepare_connection_params(params)
        self.assertEqual(result["token_duration_secs"], 900)


class TestAuroraDSQLBackend(unittest.TestCase):
    def setUp(self):
        self.wrapper = DatabaseWrapper({})
        self.ops = DatabaseOperations(connection=MagicMock())

    def test_database_wrapper_data_types(self):
        self.assertEqual(self.wrapper.data_types["BigAutoField"], "uuid")
        self.assertEqual(self.wrapper.data_types["AutoField"], "uuid")
        self.assertEqual(self.wrapper.data_types["DateTimeField"], "timestamptz")

    def test_database_wrapper_data_types_suffix(self):
        self.assertEqual(self.wrapper.data_types_suffix["BigAutoField"], "DEFAULT gen_random_uuid()")
        self.assertEqual(self.wrapper.data_types_suffix["SmallAutoField"], "")
        self.assertEqual(self.wrapper.data_types_suffix["AutoField"], "DEFAULT gen_random_uuid()")

    @patch("aurora_dsql_django.base._prepare_connection_params")
    def test_database_wrapper_get_connection_params(self, mock_prepare_params):
        mock_prepare_params.return_value = {"host": "test-host", "port": 5432, "application_name": "django"}

        with patch("django.db.backends.postgresql.base.DatabaseWrapper.get_connection_params") as mock_super:
            mock_super.return_value = {"host": "test-host", "user": "admin"}

            wrapper = DatabaseWrapper({})
            result = wrapper.get_connection_params()

        mock_prepare_params.assert_called_once()
        mock_super.assert_called_once()
        self.assertEqual(result["application_name"], "django")

    @patch("aurora_dsql_django.base.is_psycopg3", True)
    @patch("aurora_dsql_django.base.dsql_connector")
    def test_get_new_connection_psycopg3(self, mock_connector):
        mock_connection = MagicMock()
        mock_connector.DSQLConnection.connect.return_value = mock_connection

        wrapper = DatabaseWrapper({"OPTIONS": {}})
        conn_params = {"host": "test-host", "user": "admin", "application_name": "django"}

        result = wrapper.get_new_connection(conn_params)

        mock_connector.DSQLConnection.connect.assert_called_once_with(**conn_params)
        self.assertEqual(result, mock_connection)

    @patch("aurora_dsql_django.base.is_psycopg3", False)
    @patch("aurora_dsql_django.base.dsql_connector")
    @patch("psycopg2.extras.register_default_jsonb")
    def test_get_new_connection_psycopg2(self, mock_register_jsonb, mock_connector):
        mock_connection = MagicMock()
        mock_connector.connect.return_value = mock_connection

        wrapper = DatabaseWrapper({"OPTIONS": {}})
        conn_params = {"host": "test-host", "user": "admin", "application_name": "django"}

        result = wrapper.get_new_connection(conn_params)

        mock_connector.connect.assert_called_once_with(**conn_params)
        mock_register_jsonb.assert_called_once()
        self.assertEqual(result, mock_connection)

    def test_check_constraints(self):
        wrapper = DatabaseWrapper({})
        # This should not raise any exception
        wrapper.check_constraints()
        wrapper.check_constraints(table_names=["table1", "table2"])

    def test_disable_constraint_checking(self):
        wrapper = DatabaseWrapper({})
        result = wrapper.disable_constraint_checking()
        self.assertTrue(result)

    def test_enable_constraint_checking(self):
        wrapper = DatabaseWrapper({})
        # This should not raise any exception
        wrapper.enable_constraint_checking()

    def test_constraint_checks_disabled(self):
        wrapper = DatabaseWrapper({})
        with wrapper.constraint_checks_disabled():
            # This context manager should not raise any exception
            pass

    def test_autofield_rel_db_type_returns_uuid(self):
        """Test that AutoField rel_db_type returns uuid for foreign keys."""
        autofield = models.AutoField()
        bigautofield = models.BigAutoField()

        self.assertEqual(autofield.rel_db_type(self.wrapper), "uuid")
        self.assertEqual(bigautofield.rel_db_type(self.wrapper), "uuid")

    def test_autofield_get_prep_value_preserves_uuid(self):
        """Test that AutoField get_prep_value doesn't convert UUIDs to int."""
        autofield = models.AutoField()
        bigautofield = models.BigAutoField()

        test_uuid = uuid.uuid4()

        # Should preserve UUID values.
        self.assertEqual(autofield.get_prep_value(test_uuid), test_uuid)
        self.assertEqual(bigautofield.get_prep_value(test_uuid), test_uuid)

        # Should preserve None, which tells Django to use database default.
        self.assertIsNone(autofield.get_prep_value(None))
        self.assertIsNone(bigautofield.get_prep_value(None))

    def test_operations_cast_data_types(self):
        """Test that operations class maps AutoFields to uuid for casting."""
        self.assertEqual(self.ops.cast_data_types["AutoField"], "uuid")
        self.assertEqual(self.ops.cast_data_types["BigAutoField"], "uuid")

    def test_autofield_to_python_uuid_conversion(self):
        """Test that AutoField.to_python converts UUID strings to UUID objects."""
        autofield = models.AutoField()
        bigautofield = models.BigAutoField()

        # Test with valid UUID string.
        uuid_string = "8fcc0dd2-1d96-4428-a619-f0e43996dc19"

        result_auto = autofield.to_python(uuid_string)
        result_big = bigautofield.to_python(uuid_string)

        # Should convert to UUID objects.
        self.assertIsInstance(result_auto, uuid.UUID)
        self.assertIsInstance(result_big, uuid.UUID)
        self.assertEqual(str(result_auto), uuid_string)
        self.assertEqual(str(result_big), uuid_string)

    def test_autofield_to_python_with_uuid_object(self):
        """Test that AutoField.to_python handles existing UUID objects."""
        autofield = models.AutoField()
        bigautofield = models.BigAutoField()

        uuid_obj = uuid.UUID("8fcc0dd2-1d96-4428-a619-f0e43996dc19")
        result_auto = autofield.to_python(uuid_obj)
        result_big = bigautofield.to_python(uuid_obj)

        self.assertEqual(result_auto, uuid_obj)
        self.assertEqual(result_big, uuid_obj)

    def test_autofield_to_python_with_none(self):
        """Test that AutoField.to_python handles None values."""
        autofield = models.AutoField()
        bigautofield = models.BigAutoField()

        result_auto = autofield.to_python(None)
        result_big = bigautofield.to_python(None)

        self.assertIsNone(result_auto)
        self.assertIsNone(result_big)

    def test_autofield_to_python_invalid_uuid_error(self):
        """Test that AutoField.to_python raises ValidationError for invalid UUIDs."""
        autofield = models.AutoField()
        bigautofield = models.BigAutoField()

        invalid_uuid_string = "not-a-uuid"

        with self.assertRaises(ValidationError):
            autofield.to_python(invalid_uuid_string)

        with self.assertRaises(ValidationError):
            bigautofield.to_python(invalid_uuid_string)

    def test_autofield_to_python_non_uuid_type_error(self):
        """Test that AutoField.to_python raises ValidationError for non-uuid-compatible types."""
        autofield = models.AutoField()

        with self.assertRaises(ValidationError):
            autofield.to_python(123)

    def test_autofield_error_message_content(self):
        """Test that AutoField validation errors contain correct UUID message."""
        autofield = models.AutoField()

        with self.assertRaises(ValidationError) as cm:
            autofield.to_python(123)

        error_message = str(cm.exception.messages[0])
        self.assertIn("must be a valid UUID", error_message)
        self.assertIn("123", error_message)

    def test_disable_server_side_cursors_auto_set(self):
        """Test that DISABLE_SERVER_SIDE_CURSORS is automatically set to True."""
        wrapper = DatabaseWrapper(
            {
                "ENGINE": "aurora_dsql_django",
                "NAME": "test_db",
            }
        )

        self.assertTrue(wrapper.settings_dict["DISABLE_SERVER_SIDE_CURSORS"])

    def test_disable_server_side_cursors_respects_customer_setting(self):
        """Test that customer's DISABLE_SERVER_SIDE_CURSORS setting is not overridden."""
        wrapper_false = DatabaseWrapper(
            {
                "ENGINE": "aurora_dsql_django",
                "NAME": "test_db",
                # Explicit user configuration.
                "DISABLE_SERVER_SIDE_CURSORS": False,
            }
        )

        # Ensure we do not override a value that conflicts with the default.
        self.assertFalse(wrapper_false.settings_dict["DISABLE_SERVER_SIDE_CURSORS"])

        # Test with customer setting True
        wrapper_true = DatabaseWrapper(
            {
                "ENGINE": "aurora_dsql_django",
                "NAME": "test_db",
                # Explicit user configuration.
                "DISABLE_SERVER_SIDE_CURSORS": True,
            }
        )

        self.assertTrue(wrapper_true.settings_dict["DISABLE_SERVER_SIDE_CURSORS"])

    def test_disable_server_side_cursors_with_other_options(self):
        """Test that DISABLE_SERVER_SIDE_CURSORS works with other settings."""
        wrapper = DatabaseWrapper(
            {
                "ENGINE": "aurora_dsql_django",
                "NAME": "test_db",
                "OPTIONS": {
                    "sslmode": "require",
                },
            }
        )

        # Should add DISABLE_SERVER_SIDE_CURSORS while preserving other options
        self.assertTrue(wrapper.settings_dict["DISABLE_SERVER_SIDE_CURSORS"])
        self.assertEqual(wrapper.settings_dict["OPTIONS"]["sslmode"], "require")


if __name__ == "__main__":
    unittest.main()
