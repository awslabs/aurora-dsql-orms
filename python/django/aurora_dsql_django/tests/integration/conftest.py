# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import django
from django.conf import settings

# Ensure Django app registry is ready before tests that create dynamic models.
if settings.configured and not django.apps.apps.ready:
    django.setup()
