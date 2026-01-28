# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid

from django.db import models

# Create your models here.


class Owner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30, blank=False)
    # This is many to one relation
    city = models.CharField(max_length=80, blank=False)
    telephone = models.CharField(max_length=20, blank=True, null=True, default=None)

    def __str__(self):
        return f"{self.name}"


class Pet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30, blank=False)
    birth_date = models.DateField()
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, db_constraint=False, null=True)


class Specialty(models.Model):
    name = models.CharField(max_length=80, blank=False, primary_key=True)

    def __str__(self):
        return self.name


class Vet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30, blank=False)
    specialties = models.ManyToManyField(Specialty, through="VetSpecialties")
    owner = models.OneToOneField(Owner, on_delete=models.SET_DEFAULT, db_constraint=False, null=True, blank=True, default=None)

    def __str__(self):
        return f"{self.name}"


# Need to use custom intermediate table because Django considers default primary
# keys as integers. We use UUID as default primary key which is not an integer.
class VetSpecialties(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vet = models.ForeignKey(Vet, on_delete=models.CASCADE, db_constraint=False)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, db_constraint=False)


class Visits(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, db_constraint=False)
    vet = models.ForeignKey(Vet, on_delete=models.CASCADE, db_constraint=False)
    visit_date = models.DateField()
    description = models.TextField()
