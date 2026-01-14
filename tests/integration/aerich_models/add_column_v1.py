# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""V1 model for add_column migration test."""

from tortoise import fields
from tortoise.models import Model


class IncrementalTestModel(Model):
    id = fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "incremental_test_model"
