# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Models for aerich BigInt identity column tests."""

from tortoise import fields
from tortoise.models import Model

from aurora_dsql_tortoise.common import fields as dsql_fields


class CustomCacheAerichModel(Model):
    id = dsql_fields.BigIntField(primary_key=True, sequence_cache_size=1)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "custom_cache_aerich_model"
