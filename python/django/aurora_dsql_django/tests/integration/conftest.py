# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import django

# Ensure Django app registry is ready before tests that create dynamic models.
django.setup()
