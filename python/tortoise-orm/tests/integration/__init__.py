# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import sys

import pytest


def run():
    sys.exit(pytest.main(["-v", "tests/integration/"]))
