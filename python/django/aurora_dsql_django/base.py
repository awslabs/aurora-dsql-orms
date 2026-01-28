# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Aurora DSQL adapter for Django.

This module extends Django's PostgreSQL backend to work with Aurora DSQL,
using the aurora-dsql-python-connector for automatic IAM authentication.
"""

import logging
import uuid

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.db.backends.postgresql import base
from django.db.backends.postgresql.psycopg_any import IsolationLevel, is_psycopg3
from django.db.models.fields import Field
from django.utils.asyncio import async_unsafe
from django.utils.translation import gettext_lazy

from .creation import DatabaseCreation
from .features import DatabaseFeatures
from .operations import DatabaseOperations
from .schema import DatabaseSchemaEditor

logger = logging.getLogger(__name__)

# Import the appropriate connector based on psycopg version
try:
    import aurora_dsql_psycopg as dsql_connector
except ImportError:
    import aurora_dsql_psycopg2 as dsql_connector


def _prepare_connection_params(params):
    """
    Prepare connection parameters for the Aurora DSQL connector.

    Sets defaults for DSQL connections.

    Args:
        params (dict): Connection parameters from Django settings

    Returns:
        dict: Parameters ready for the DSQL connector
    """
    # Set default sslrootcert to system certs if using verify-full
    sslmode = params.get("sslmode", None)
    sslrootcert = params.get("sslrootcert", None)
    if sslrootcert is None and sslmode == "verify-full":
        params["sslrootcert"] = "system"

    # Add application_name for tracking (connector will format as django:aurora-dsql-python-psycopg/<version>)
    params["application_name"] = "django"

    return params


class DatabaseWrapper(base.DatabaseWrapper):
    """
    A wrapper class that adapts the Django PostgreSQL backend for Aurora DSQL.

    Uses aurora-dsql-python-connector for automatic IAM authentication.
    """

    vendor = "dsql"
    display_name = "Aurora DSQL"
    # Override some types from the postgresql adapter.
    data_types = dict(
        base.DatabaseWrapper.data_types,
        BigAutoField="uuid",
        AutoField="uuid",
        DateTimeField="timestamptz",
    )
    data_types_suffix = dict(
        base.DatabaseWrapper.data_types_suffix,
        BigAutoField="DEFAULT gen_random_uuid()",
        # For now skipping small int because uuid does not fit in a smallint?
        SmallAutoField="",
        AutoField="DEFAULT gen_random_uuid()",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._patch_autofields()

        # Automatically disable server-side cursors since Aurora DSQL doesn't support them.
        # We preserve the user config if it is defined but this is likely a user mistake.
        self.settings_dict.setdefault("DISABLE_SERVER_SIDE_CURSORS", True)

    def _patch_autofields(self):
        """
        Patch AutoField classes to return UUID type for related fields.
        This ensures ForeignKey fields that reference AutoFields are also UUIDs.
        """

        def uuid_rel_db_type(self, connection):
            return "uuid"

        def uuid_get_prep_value(self, value):
            """Override get_prep_value to prevent int() conversion of UUIDs."""
            return Field.get_prep_value(self, value)

        def uuid_to_python(self, value):
            """Convert provided value to a UUID where possible."""
            if value is None or isinstance(value, uuid.UUID):
                return value
            if isinstance(value, str):
                try:
                    return uuid.UUID(value)
                except ValueError:
                    pass

            raise ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value},
            )

        for field_class in [models.AutoField, models.BigAutoField]:
            field_class.rel_db_type = uuid_rel_db_type
            field_class.get_prep_value = uuid_get_prep_value
            field_class.to_python = uuid_to_python
            field_class.default_error_messages = {
                "invalid": gettext_lazy("'%(value)s' value must be a valid UUID."),
            }

    SchemaEditorClass = DatabaseSchemaEditor
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    ops_class = DatabaseOperations

    def get_connection_params(self):
        params = super().get_connection_params()
        return _prepare_connection_params(params)

    @async_unsafe
    def get_new_connection(self, conn_params):
        """
        Create a new connection to Aurora DSQL using the connector.

        The connector handles IAM authentication automatically.
        """
        options = self.settings_dict["OPTIONS"]
        isolation_level_value = options.get("isolation_level")

        if isolation_level_value is None:
            self.isolation_level = IsolationLevel.READ_COMMITTED
        else:
            try:
                self.isolation_level = IsolationLevel(isolation_level_value)
            except ValueError:
                raise ImproperlyConfigured(
                    f"Invalid transaction isolation level {isolation_level_value} "
                    f"specified. Use one of the psycopg.IsolationLevel values."
                )

        if is_psycopg3:
            connection = dsql_connector.DSQLConnection.connect(**conn_params)
        else:
            connection = dsql_connector.connect(**conn_params)

        if isolation_level_value is not None:
            connection.isolation_level = self.isolation_level

        if not is_psycopg3:
            import psycopg2.extras

            psycopg2.extras.register_default_jsonb(conn_or_curs=connection, loads=lambda x: x)

        return connection

    def check_constraints(self, table_names=None):
        """
        Override to do nothing since SET CONSTRAINTS is not supported.
        """

    def disable_constraint_checking(self):
        """
        Override to do nothing since SET CONSTRAINTS is not supported.
        """
        return True

    def enable_constraint_checking(self):
        """
        Override to do nothing since SET CONSTRAINTS is not supported.
        """
