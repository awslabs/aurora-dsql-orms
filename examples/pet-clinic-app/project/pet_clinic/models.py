# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with
# the License. A copy of the License is located at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

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
