# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aurora_dsql_django")
except PackageNotFoundError:
    __version__ = "unknown"
