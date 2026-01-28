# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
This module customizes the default Django database creation for Aurora DSQL.
In order to customize the database creation process, the module overrides
certain functions with custom logic.
"""

from django.db.backends.postgresql import creation


class DatabaseCreation(creation.DatabaseCreation):
    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        raise NotImplementedError(
            "Aurora DSQL doesn't support cloning databases. Disable the option to run tests in parallel processes."
        )
