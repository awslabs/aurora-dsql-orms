# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from importlib.metadata import PackageNotFoundError, version
from .fields import SequenceAutoField

try:
    __version__ = version("aurora_dsql_django")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["SequenceAutoField"]
