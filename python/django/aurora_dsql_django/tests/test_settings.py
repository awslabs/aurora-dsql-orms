# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

cluster_endpoint = os.environ.get("CLUSTER_ENDPOINT", None)
if cluster_endpoint is None:
    sys.exit("CLUSTER_ENDPOINT environment variable is not set")

# Override with our test-specific settings
# Note: The aurora-dsql-python-connector automatically extracts the region
# from the cluster endpoint hostname, so no need to specify it in OPTIONS.
DATABASES = {
    "default": {
        "HOST": cluster_endpoint,
        "USER": "admin",
        "NAME": "postgres",
        "ENGINE": "aurora_dsql_django",
        "PORT": "5432",
        "OPTIONS": {
            "sslmode": "verify-full",
        },
    }
}
USE_TZ = True

# Add other necessary Django settings
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    # Add other apps as needed
]

# Disable Django's transaction management
DISABLE_TRANSACTION_MANAGEMENT = True
