# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import html
import json
import time

from django.db import Error
from django.db.transaction import atomic
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from pet_clinic.models import Owner, Pet, Specialty, Vet, VetSpecialties

# Create your views here.


##
# initial_wait is the amount of time after with the operation is retried
# delay_factor is the pace at which the retries slow down upon each failure.
# For example an initial_wait of 1 and delay_factor of 2 implies,
# First retry occurs after 1 second, second one after 1*2 = 2 seconds,
# Third one after 2*2 = 4 seconds, forth one after 4*2 = 8 seconds and so on.
##
def with_retries(retries=3, failed_response=HttpResponse(status=500), initial_wait=1, delay_factor=2):
    def handle(view):
        def retry_fn(*args, **kwargs):
            delay = initial_wait
            for i in range(retries):
                print(("attempt: %s/%s") % (i + 1, retries))
                try:
                    return view(*args, **kwargs)
                # TODO: check error code?
                except Error as e:
                    print(f"Error: {e}, retrying...")
                    time.sleep(delay)
                    delay *= delay_factor
            return failed_response

        return retry_fn

    return handle


@method_decorator(csrf_exempt, name="dispatch")
class OwnerView(View):
    @with_retries()
    def get(self, request, id=None, *args, **kwargs):
        owners = Owner.objects
        # Apply filter if specific id is requested.
        if id is not None:
            owners = owners.filter(id=id)
        return JsonResponse(list(owners.values()), safe=False)

    @with_retries()
    @atomic
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode())

        # If id is provided we try updating the existing object
        id = data.get("id", None)
        try:
            owner = Owner.objects.get(id=id) if id is not None else None
        except Exception:
            return HttpResponseBadRequest(("error: check if owner with id `%s` exists") % (html.escape(str(id))))

        name = data.get("name", owner.name if owner else None)
        # Either the name or id must be provided.
        if owner is None and name is None:
            return HttpResponseBadRequest()

        telephone = data.get("telephone", owner.telephone if owner else None)
        city = data.get("city", owner.city if owner else None)

        if owner is None:
            # Owner _not_ present, creating new one
            print(("owner: %s is not present; adding") % (name))
            owner = Owner(name=name, telephone=telephone, city=city)
        else:
            # Owner present, update existing
            print(("owner: %s is present; updating") % (name))
            owner.name = name
            owner.telephone = telephone
            owner.city = city

        owner.save()
        return JsonResponse(list(Owner.objects.filter(id=owner.id).values()), safe=False)

    @with_retries()
    @atomic
    def delete(self, request, id=None, *args, **kwargs):
        if id is not None:
            Owner.objects.filter(id=id).delete()
        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name="dispatch")
class PetView(View):
    @with_retries()
    def get(self, request=None, id=None, *args, **kwargs):
        pets = Pet.objects
        # Apply filter if specific id is requested.
        if id is not None:
            pets = pets.filter(id=id)
        return JsonResponse(list(pets.values()), safe=False)

    @with_retries()
    @atomic
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode())

        # If id is provided we try updating the existing object
        id = data.get("id", None)
        try:
            pet = Pet.objects.get(id=id) if id is not None else None
        except Exception:
            return HttpResponseBadRequest(("error: check if pet with id `%s` exists") % (html.escape(str(id))))

        name = data.get("name", pet.name if pet else None)
        # Either the name or id must be provided.
        if pet is None and name is None:
            return HttpResponseBadRequest()

        birth_date = data.get("birth_date", pet.birth_date if pet else None)
        owner_id = data.get("owner_id", pet.owner.id if pet and pet.owner else None)
        try:
            owner = Owner.objects.get(id=owner_id) if owner_id else None
        except Exception:
            return HttpResponseBadRequest(("error: check if owner with id `%s` exists") % (html.escape(str(owner_id))))

        if pet is None:
            # Pet _not_ present, creating new one
            print(("pet name: %s is not present; adding") % (name))
            pet = Pet(name=name, birth_date=birth_date, owner=owner)
        else:
            # Pet present, update existing
            print(("pet name: %s is present; updating") % (name))
            pet.name = name
            pet.birth_date = birth_date
            pet.owner = owner

        pet.save()
        return JsonResponse(list(Pet.objects.filter(id=pet.id).values()), safe=False)

    @with_retries()
    @atomic
    def delete(self, request=None, id=None, *args, **kwargs):
        if id is not None:
            Pet.objects.filter(id=id).delete()
        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name="dispatch")
class VetView(View):
    @with_retries()
    def get(self, request=None, id=None, *args, **kwargs):
        vets = Vet.objects
        # Apply filter if specific id is requested.
        if id is not None:
            vets = vets.filter(id=id)
        return JsonResponse(list(vets.values()), safe=False)

    @with_retries()
    @atomic
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode())
        # If id is provided we try updating the existing object
        id = data.get("id", None)
        try:
            vet = Vet.objects.get(id=id) if id is not None else None
        except Exception:
            return HttpResponseBadRequest(("error: check if vet with id `%s` exists") % (html.escape(str(id))))

        name = data.get("name", vet.name if vet else None)

        # Either the name or id must be provided.
        if vet is None and name is None:
            return HttpResponseBadRequest()

        owner_id = data.get("owner_id", vet.owner.id if vet and vet.owner else None)
        try:
            owner = Owner.objects.get(id=owner_id) if owner_id else None
        except Exception:
            return HttpResponseBadRequest(("error: check if owner with id `%s` exists") % (html.escape(str(id))))

        specialties_list = data.get("specialties", vet.specialties if vet and vet.specialties else [])
        specialties = []
        for specialty in specialties_list:
            try:
                specialties_obj = Specialty.objects.get(name=specialty)
            except Exception:
                return HttpResponseBadRequest(("error: check if specialty `%s` exists") % (html.escape(str(specialty))))
            specialties.append(specialties_obj)

        if vet is None:
            print(("vet name: %s, not present, adding") % (name))
            vet = Vet(name=name, owner_id=owner_id)
        else:
            print(("vet name: %s, present, updating") % (name))
            vet.name = name
            vet.owner = owner

        # First save the vet so that we have an id. Then we can add specialties.
        # Django needs the id primary key of the parent object before adding relations
        vet.save()

        # Add any specialties provided
        vet.specialties.add(*specialties)
        return JsonResponse(
            {
                "Veterinarian": list(Vet.objects.filter(id=vet.id).values()),
                "Specialties": list(VetSpecialties.objects.filter(vet=vet.id).values()),
            },
            safe=False,
        )

    @with_retries()
    @atomic
    def delete(self, request, id=None, *args, **kwargs):
        if id is not None:
            Vet.objects.filter(id=id).delete()
        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name="dispatch")
class SpecialtyView(View):
    @with_retries()
    def get(self, request=None, name=None, *args, **kwargs):
        specialties = Specialty.objects
        # Apply filter if specific name is requested.
        if name is not None:
            specialties = specialties.filter(name=name)
        return JsonResponse(list(specialties.values()), safe=False)

    @with_retries()
    @atomic
    def post(self, request=None, *args, **kwargs):
        data = json.loads(request.body.decode())
        name = data.get("name", None)
        if name is None:
            return HttpResponseBadRequest()
        specialty = Specialty(name=name)
        specialty.save()
        return JsonResponse(list(Specialty.objects.filter(name=specialty.name).values()), safe=False)

    @with_retries()
    @atomic
    def delete(self, request=None, name=None, *args, **kwargs):
        if id is not None:
            Specialty.objects.filter(name=name).delete()
        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name="dispatch")
class VetSpecialtiesView(View):
    @with_retries()
    def get(self, request=None, *args, **kwargs):
        data = json.loads(request.body.decode())
        vet_id = data.get("vet_id", None)
        specialty_id = data.get("specialty_id", None)
        specialties = VetSpecialties.objects
        # Apply filter if specific name is requested.
        if vet_id is not None:
            specialties = specialties.filter(vet_id=vet_id)
        if specialty_id is not None:
            specialties = specialties.filter(specialty_id=specialty_id)
        return JsonResponse(list(specialties.values()), safe=False)
