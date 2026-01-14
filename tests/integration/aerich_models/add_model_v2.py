# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""V2 model for incremental migration tests - adds SecondModel."""

from tortoise import fields
from tortoise.models import Model


class ExistingModel(Model):
    id = fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "existing_model"


class SecondModel(Model):
    id = fields.UUIDField(primary_key=True)
    title = fields.CharField(max_length=200)

    class Meta:
        table = "second_model"
