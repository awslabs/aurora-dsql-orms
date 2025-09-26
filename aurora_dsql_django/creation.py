# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with
# the License. A copy of the License is located at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file.
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.

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
