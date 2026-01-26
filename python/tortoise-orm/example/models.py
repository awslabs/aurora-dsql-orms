# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid

from tortoise import fields
from tortoise.models import Model


class Owner(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=30)
    city = fields.CharField(max_length=80)
    telephone = fields.CharField(max_length=20, null=True)
    email = fields.CharField(max_length=100, null=True)

    pets: fields.ReverseRelation["Pet"]

    class Meta:
        table = "owner"


class Pet(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=30)
    birth_date = fields.DateField()
    owner: fields.ForeignKeyNullableRelation[Owner] = fields.ForeignKeyField(
        "models.Owner", related_name="pets", null=True
    )

    class Meta:
        table = "pet"


class Specialty(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=80)

    class Meta:
        table = "specialty"


class Vet(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=30)
    specialties: fields.ManyToManyRelation[Specialty] = fields.ManyToManyField(
        "models.Specialty", related_name="vets", through="vetSpecialties"
    )

    class Meta:
        table = "vet"
