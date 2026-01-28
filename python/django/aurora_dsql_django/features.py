# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
A module with custom wrapper that overrides base postgres database features
adapter in order to make it work with Aurora DSQL. Certain Django features can
be enabled and disabled using this adapter.
"""

from django.db.backends.postgresql import features


class DatabaseFeatures(features.DatabaseFeatures):
    # Can run a DDL inside a transaction.
    # If true, multiple DDL statement are run in same transaction.
    can_rollback_ddl = False

    # Can a fixture contain forward references? i.e., are
    # FK constraints checked at the end of transaction, or
    # at the end of each save operation?
    supports_forward_references = True

    supports_foreign_keys = False

    supports_table_check_constraints = False

    # Can it create foreign key constraints inline when adding columns?
    can_create_inline_fk = False

    # Can the backend clone databases for parallel test execution?
    # Defaults to False to allow third-party backends to opt-in.
    can_clone_databases = False

    # Can constraint checks be deferred until the end of a transaction?
    can_defer_constraint_checks = False

    # Does the database support deferrable unique constraints?
    supports_deferrable_unique_constraints = False

    # Does the database have native JSON field support?
    has_native_json_field = False

    # Can the database introspect materialized views?
    can_introspect_materialized_views = False

    # Can the database rename an index?
    can_rename_index = True

    supports_expression_indexes = False

    # Does the database use savepoints for nested transactions?
    uses_savepoints = False

    # Can savepoints be released, allowing partial rollback of nested
    # transactions?
    can_release_savepoints = False
