# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""V2 model for multi-model migration test - adds two models at once."""

from tortoise import fields
from tortoise.models import Model


class BaseModel(Model):
    id = fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "multi_base_model"


class ModelA(Model):
    id = fields.UUIDField(primary_key=True)
    value_a = fields.CharField(max_length=100)

    class Meta:
        table = "multi_model_a"


class ModelB(Model):
    id = fields.UUIDField(primary_key=True)
    value_b = fields.IntField()

    class Meta:
        table = "multi_model_b"
