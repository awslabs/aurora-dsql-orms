# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Models for aerich integration tests."""

from tortoise import fields
from tortoise.models import Model


class AerichTestModel(Model):
    id = fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "aerich_test_model"
