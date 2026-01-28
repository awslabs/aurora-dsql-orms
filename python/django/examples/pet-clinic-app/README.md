# How to build an web app with Django using Aurora DSQL as database

## Bootstrap the Django App
### Pre-requisites
- Provision a Aurora DSQL cluster and note the hostname
- Python version >=3.10 must have been installed

### Bootstrap Django app
1. Create a new directory named `django_aurora_dsql_example` and change to the new directory
   ```sh
   mkdir django_dsql_example
   cd django_dsql_example
   ```
2. Install django and other requirements.
   
   a. Create a requirements.txt file and add following requirements into it.
      ```sh
      django
      psycopg[binary]
      aurora_dsql_django
      ```
   b. Create a [python virtual environment](https://docs.python.org/3/library/venv.html)
      and activate it.
      ```sh
      python3 -m venv venv
      source venv/bin/activate
      ``` 
   c. Install all requirements defined in the requirements file
      ```sh
      pip install --force-reinstall -r requirements.txt
      ```
   d. Make sure django is installed
      ```sh
      > python3 -m django --version                      
        5.1.2 # you may have a different version
      ```
   At the end of this step, the directory structure should look like this
   ```sh
   # NOTE: Your artifact versions may be different
   ├ django_aurora_dsql_example
   └── requirements.txt
   └── venv/
   ```
3. Bootstrap django project
   
   a. Create a django project and change directory
   ```sh
   django-admin startproject project
   cd project
   ```
   b. Create pet_clinic django app
   ```sh
   python3 manage.py startapp pet_clinic
   ```
   At the end of this step, the directory structure should look like below
   ```sh
   ├ django_aurora_dsql_example
   ├── project 
   │   ├── manage.py
   │   ├── pet_clinic 
   │   │   ├── __init__.py
   │   │   ├── admin.py
   │   │   ├── apps.py
   │   │   ├── migrations
   │   │   │   └── __init__.py
   │   │   ├── models.py
   │   │   ├── tests.py
   │   │   └── views.py
   │   └── project 
   │       ├── __init__.py
   │       ├── asgi.py
   │       ├── settings.py
   │       ├── urls.py
   │       └── wsgi.py
   └── requirements.txt
   └── venv/
   ```
4. Django comes with default auth and admin apps installed with it which do not
   work with Aurora DSQL. Find the few variables in `django_aurora_dsql_example/project/project/settings.py` 
   and set values as described below 
   ```sh
   ALLOWED_HOSTS = ['*']
   INSTALLED_APPS = ['pet_clinic'] # Ensure you have the pet_clinic app defined here.
   MIDDLEWARE = []
   TEMPLATES = [
      {
         'BACKEND': 'django.template.backends.django.DjangoTemplates',
         'DIRS': [],
         'APP_DIRS': True,
         'OPTIONS': {
            'context_processors': [
               'django.template.context_processors.debug',
               'django.template.context_processors.request',
            ],
         },
      },
   ]
   ```
5. Remove the references to `admin` app in the django project.

   a. From `django_aurora_dsql_example/project/project/urls.py` remove path to admin page.
      ```
      # remove the following line
      from django.contrib import admin

      # make sure that urlpatterns variable is an empty array like below
      urlpatterns = []
      ```
   b. From `django_aurora_dsql_example/project/pet_clinic` delete the `admin.py` file.

6. Change the database settings such that the app uses Aurora DSQL cluster instead of default
   sqlite3.

   ```sh
   DATABASES = {
      'default': {
         # Provide the hostname of the cluster
         'HOST': <cluster hostname>, #Eg: <cluster-id>.dsql.us-east-1.on.aws
         'USER': 'admin',
         'NAME': 'postgres',
         'ENGINE': 'aurora_dsql_django', # This is the custom database adapter for Aurora DSQL
         'OPTIONS': {
               'sslmode': 'require',
         }
      }
   }
   ```

## Making the app 
By now we have bootstrapped the Django pet clinic. We can now add models, create views
and run the server.

> [!Important]
> To execute example code, you need to have the valid aws credentials.

### Create Models
Our pet clinic as Pets, Owners of pets, veterinarians and specialties of those Veterinarians.
A owner can visit the resident veterinarian in the clinic with their pet.

- One owner can have many pets (one-to-many) / (many-to-one in the reverse)
- A veterinarian can have any number of specialties and a specialty can be associated
  with any number of veterinarians (many-to-many)

> [!Important]
> Aurora DSQL does not support the auto incrementing SERIAL type primary key.
> We must use a different different primary key. In this example, we are going to use
> a UUIDField with a default uuid value for the primary key.

```python
from django.db import models
import uuid

# Create your models here.

class Owner(models.Model):
    # SERIAL Auto incrementing primary keys are not supported. Using UUID instead.
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=30, blank=False)
    # This is many to one relation
    city = models.CharField(max_length=80, blank=False)
    telephone = models.CharField(max_length=20, blank=True, null=True, default=None)

    def __str__(self):
        return f'{self.name}'
    
class Pet(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=30, blank=False)
    birth_date = models.DateField()
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, db_constraint=False, null=True)
```

To create associated tables in the Aurora DSQL cluster run following commands in
`django_aurora_dsql_example/project` directory

```sh
# This will generate 0001_Initial.py in django_Aurora DSQL_example/project/pet_clinic directory
python3 manage.py makemigrations pet_clinic
python3 manage.py migrate pet_clinic 0001
```

### Create Views
Now that we have models and corresponding tables, we are ready to create views for each
model. We will implement CRUD for each model.

> 
> Note that we do not want to give up upon error immediately. For example, the transaction
> may fail because of a Optimistic Concurrency Control (OCC) error. Instead of giving up
> immediately, we can retry N times. In this example, we are attempting the operation 3 times
> by default. In order to achieve this a sample `with_retry` method is provided here.
> 

```python
from django.shortcuts import render, redirect
from django.views import generic
from django.views.generic import View
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.db.transaction import atomic
from psycopg import errors
from django.db import Error, IntegrityError
import json, time, datetime

from pet_clinic.models import *

##
# If there is an error, we want to retry instead of giving up immediately. 
# initial_wait is the amount of time after with the operation is retried
# delay_factor is the pace at which the retries slow down upon each failure.
# For example an initial_wait of 1 and delay_factor of 2 implies,
# First retry occurs after 1 second, second one after 1*2 = 2 seconds,
# Third one after 2*2 = 4 seconds, forth one after 4*2 = 8 seconds and so on.
##
def with_retries(retries = 3, failed_response = HttpResponse(status=500), initial_wait = 1, delay_factor = 2):
    def handle(view):
        def retry_fn(*args, **kwargs):
            delay = initial_wait
            for i in range(retries):
                print(("attempt: %s/%s") % (i+1, retries))
                try:
                    return view(*args, **kwargs)
                except Error as e:
                    print(f"Error: {e}, retrying...")
                    time.sleep(delay)
                    delay *= delay_factor
            return failed_response
        return retry_fn
    return handle

@method_decorator(csrf_exempt, name='dispatch')
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
        id = data.get('id', None)
        try:
            owner = Owner.objects.get(id=id) if id is not None else None
        except:
            return HttpResponseBadRequest(("error: check if owner with id `%s` exists") % (id))
                     
        name = data.get('name', owner.name if owner else None)
        # Either the name or id must be provided.
        if owner is None and name is None:
            return HttpResponseBadRequest()
        
        telephone = data.get('telephone', owner.telephone if owner else None)
        city = data.get('city', owner.city if owner else None)
        
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
    
@method_decorator(csrf_exempt, name='dispatch')
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
        id = data.get('id', None)
        try:
            pet = Pet.objects.get(id=id) if id is not None else None
        except:
            return HttpResponseBadRequest(("error: check if pet with id `%s` exists") % (id))
        
        name = data.get('name', pet.name if pet else None)
        # Either the name or id must be provided.
        if pet is None and name is None:
            return HttpResponseBadRequest()
        
        birth_date = data.get('birth_date', pet.birth_date if pet else None)
        owner_id = data.get('owner_id', pet.owner.id if pet and pet.owner else None)
        try:
            owner = Owner.objects.get(id=owner_id) if owner_id else None
        except:
            return HttpResponseBadRequest(("error: check if owner with id `%s` exists") % (owner_id))
        
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
```

### Add routes
Modify the `django_aurora_dsql_example/project/project/urls.py` to have the following code.
With this code we are creating API paths that permit performing CRUD operations
on the data.

```python
from django.contrib import admin
from django.urls import path
from pet_clinic.views import *

urlpatterns = [
    path('owner/', OwnerView.as_view(), name='owner'),
    path('owner/<id>', OwnerView.as_view(), name='owner'),
    path('pet/', PetView.as_view(), name='pet'),
    path('pet/<id>', PetView.as_view(), name='pet'),
]
```
### Test
We can now test our app by sending it queries. Remember to start the Django app by
running following command.
```sh
python3 manage.py runserver
```

#### CRUD operations on Owners
----

##### Create/Update
```sh
curl --request POST --data '{"name":"Joe", "city":"Seattle"}' http://0.0.0.0:8000/owner/
curl --request POST --data '{"name":"Mary", "telephone":"93209753297", "city":"New York"}' http://0.0.0.0:8000/owner/
curl --request POST --data '{"name":"Dennis", "city":"Chicago"}' http://0.0.0.0:8000/owner/
```

##### (Read) List all owners
```sh
curl --request GET http://0.0.0.0:8000/owner/
```

##### List details of particular owner
```sh
curl --request GET http://0.0.0.0:8000/owner/44ca64ed-0264-450b-817b-14386c7df277
```

##### Update an owner's city
Provide the id of existing owner and updated details
```sh
curl --request POST --data '{"id":"44ca64ed-0264-450b-817b-14386c7df277", "city":"Vancouver"}' http://0.0.0.0:8000/owner/
```

##### Delete an owner
```sh
curl --request DELETE http://0.0.0.0:8000/owner/44ca64ed-0264-450b-817b-14386c7df277
```

#### CRUD operations on Pets
----

##### Create
```sh
curl --request POST --data '{"name":"Tom", "birth_date":"2006-10-25"}' http://0.0.0.0:8000/pet/
curl --request POST --data '{"name":"luna", "birth_date":"2020-10-10"}' http://0.0.0.0:8000/pet/
curl --request POST --data '{"name":"Myna", "birth_date":"2021-09-11"}' http://0.0.0.0:8000/pet/
```

##### (Read) List all pets 
```sh
curl --request GET http://0.0.0.0:8000/pet/
```

##### List details of particular pet
```sh
curl --request GET http://0.0.0.0:8000/pet/f397b51b-2fdd-441d-b0ac-f115acd74725
```

##### Update
```sh
# Update Tom's date of birth
curl --request POST --data '{"id":"f397b51b-2fdd-441d-b0ac-f115acd74725", "birth_date":"2016-09-11"}' http://0.0.0.0:8000/pet/
```

##### Delete a pet
```sh
curl --request DELETE http://0.0.0.0:8000/pet/f397b51b-2fdd-441d-b0ac-f115acd74725
```

## Relationships

### One-to-many / Many-to-one
These relationships can be achieved by having the foreign key constraint on the
field. For example, an owner can have any number of pets. A pet can have only one
owner.

```sh
# An owner can adopt a pet
curl --request POST --data '{"id":"d52b4b69-b5f7-49a9-90af-adfdf10ecc03", "owner_id":"0f7cd839-c8ee-436e-baf3-e52aaa51fa65"}' http://0.0.0.0:8000/pet/

# Same owner can have another pet
curl --request POST --data '{"id":"485c8818-d7c1-4965-a024-0e133896c72d", "owner_id":"0f7cd839-c8ee-436e-baf3-e52aaa51fa65"}' http://0.0.0.0:8000/pet/

# Deleting the owner deletes pets as ForeignKey is configured with on_delete.CASCADE
curl --request DELETE http://0.0.0.0:8000/owner/0f7cd839-c8ee-436e-baf3-e52aaa51fa65

# Confirm that owner is deleted
curl --request GET http://0.0.0.0:8000/owner/12154d97-0f4c-4fed-b560-6578d46aff6d

# Confirm corresponding pets are deleted
curl --request GET http://0.0.0.0:8000/pet/d52b4b69-b5f7-49a9-90af-adfdf10ecc03
curl --request GET http://0.0.0.0:8000/pet/485c8818-d7c1-4965-a024-0e133896c72d
```

### Many-to-Many
To illustrate Many-to-many we can imagine having a list of specialties and a
list of veterinarian. A specialty can be attributed to any number of veterinarians
and a veterinarian can have any number of specialties. In order to achieve this
we will create ManyToMany mapping. As our primary keys are non integer UUIDs, we
cannot directly use ManyToMany. We need to define a mapping via custom intermediate
table with explicit UUID as the primary key.

### One-to-One
To illustrate One-to-One let's imagine that Vet can also be a owner. This imposes
one-to-one relationship between the Vet and the owner. Also, not all Vets are owners. 
We define this by having a OneToOne field named `owner` in the Vet model and 
flagging it can be blank or null but it must be unique.

> [!Important]
> Django treats all AutoFields as integers internally. And Django automatically creates
> an intermediate table to manage many-to-many mapping with a Auto increment column as
> primary key. Aurora DSQL does not support this so we will create an intermediate ourselves
> instead of letting Django do it automatically.

#### Define models
```python
class Specialty(models.Model):
    name = models.CharField(max_length=80, blank=False, primary_key=True)
    def __str__(self):
        return self.name
    
class Vet(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=30, blank=False)
    specialties = models.ManyToManyField(Specialty, through='VetSpecialties')
    owner = models.OneToOneField(Owner, on_delete=models.SET_DEFAULT, db_constraint=False, null=True, blank=True, default=None)
    def __str__(self):
        return f'{self.name}'

# Need to use custom intermediate table because Django considers default primary
# keys as integers. We use UUID as default primary key which is not an integer.
class VetSpecialties(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    vet = models.ForeignKey(Vet, on_delete=models.CASCADE, db_constraint=False)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, db_constraint=False)
```

#### Define views
Like the view we have created for Owners and Pets, we define the views for Specialties and and Vets. 
We can follow the similar CRUD pattern that we followed for Owners and pets.

```python
@method_decorator(csrf_exempt, name='dispatch')
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
        name = data.get('name', None)
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

@method_decorator(csrf_exempt, name='dispatch')
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
        id = data.get('id', None)
        try:
            vet = Vet.objects.get(id=id) if id is not None else None
        except:
            return HttpResponseBadRequest(("error: check if vet with id `%s` exists") % (id))
        
        name = data.get('name', vet.name if vet else None)
        
        # Either the name or id must be provided.
        if vet is None and name is None:
            return HttpResponseBadRequest()
        
        owner_id = data.get('owner_id', vet.owner.id if vet and vet.owner else None)
        try:
            owner = Owner.objects.get(id=owner_id) if owner_id else None
        except:
            return HttpResponseBadRequest(("error: check if owner with id `%s` exists") % (id))
        
        specialties_list = data.get('specialties', vet.specialties if vet and vet.specialties else [])
        specialties = []
        for specialty in specialties_list:
            try:
                specialties_obj = Specialty.objects.get(name=specialty)
            except Exception:
                return HttpResponseBadRequest(("error: check if specialty `%s` exists") % (specialty))
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
                'Veterinarian': list(Vet.objects.filter(id=vet.id).values()), 
                'Specialties': list(VetSpecialties.objects.filter(vet=vet.id).values())
            }, safe=False)

    @with_retries()
    @atomic
    def delete(self, request, id=None, *args, **kwargs):
        if id is not None:
            Vet.objects.filter(id=id).delete()
        return HttpResponse(status=200)

@method_decorator(csrf_exempt, name='dispatch')
class VetSpecialtiesView(View):
    @with_retries()
    def get(self, request=None, *args, **kwargs):
        data = json.loads(request.body.decode())
        vet_id = data.get('vet_id', None)
        specialty_id = data.get('specialty_id', None)
        specialties = VetSpecialties.objects
        # Apply filter if specific name is requested.
        if vet_id is not None:
            specialties = specialties.filter(vet_id=vet_id)
        if specialty_id is not None:
            specialties = specialties.filter(specialty_id=specialty_id)
        return JsonResponse(list(specialties.values()), safe=False)
```

#### Update Routes

Modify the `django_aurora_dsql_example/project/project/urls.py` and ensure that `urlpatterns`.
variable is set like below

```python
urlpatterns = [
    path('owner/', OwnerView.as_view(), name='owner'),
    path('owner/<id>', OwnerView.as_view(), name='owner'),
    path('pet/', PetView.as_view(), name='pet'),
    path('pet/<id>', PetView.as_view(), name='pet'),
    path('vet/', VetView.as_view(), name='vet'),
    path('vet/<id>', VetView.as_view(), name='vet'),
    path('specialty/', SpecialtyView.as_view(), name='specialty'),
    path('specialty/<name>', SpecialtyView.as_view(), name='specialty'),
    path('vet-specialties/<vet_id>', VetSpecialtiesView.as_view(), name='vet-specialties'),
    path('specialty-vets/<specialty_id>', VetSpecialtiesView.as_view(), name='vet-specialties'),
]
```

#### Test many to many

##### Create some specialties
```sh
curl --request POST --data '{"name":"Exotic"}' http://0.0.0.0:8000/specialty/
curl --request POST --data '{"name":"Dogs"}' http://0.0.0.0:8000/specialty/
curl --request POST --data '{"name":"Cats"}' http://0.0.0.0:8000/specialty/
curl --request POST --data '{"name":"Pandas"}' http://0.0.0.0:8000/specialty/
```

##### Create few veterinarians 
We can have vets with many specialties and same specialty can be attributed to many vets.
If you try adding a specialty that does not exit, an error will be returned.
```sh
curl --request POST --data '{"name":"Jake", "specialties": ["Dogs", "Cats"]}' http://0.0.0.0:8000/vet/
curl --request POST --data '{"name":"Vince", "specialties": ["Dogs"]}' http://0.0.0.0:8000/vet/
curl --request POST --data '{"name":"Matt"}' http://0.0.0.0:8000/vet/
# Update Matt to have specialization in Cats and Exotic animals
curl --request POST --data '{"id":"2843be51-a26b-42b6-9e20-c3f2eba6e949", "specialties": ["Dogs", "Cats"]}' http://0.0.0.0:8000/vet/
```

##### Delete
Deleting the specialty will update list of specialties associated with the veterinarian because
we have setup the CASCADE delete constraint.
```sh
# Check the list of vets who has the Dogs specialty attributed
curl --request GET --data '{"specialty_id":"Dogs"}' http://0.0.0.0:8000/vet-specialties/
# Delete dogs specialty, in our sample queries there are two vets who has this specialty
curl --request DELETE http://0.0.0.0:8000/specialty/Dogs
# We can now check that vets specialties are updated. The Dogs specialty must have been removed from the vet's specialties.
curl --request GET --data '{"vet_id":"2843be51-a26b-42b6-9e20-c3f2eba6e949"}' http://0.0.0.0:8000/vet-specialties/
```

#### Test One-to-one

##### Create few owners
```sh
curl --request POST --data '{"name":"Paul", "city":"Seattle"}' http://0.0.0.0:8000/owner/
curl --request POST --data '{"name":"Pablo", "city":"New York"}' http://0.0.0.0:8000/owner/
# Note down owner ids
```

##### Create some specialties
```sh
curl --request POST --data '{"name":"Exotic"}' http://0.0.0.0:8000/specialty/
curl --request POST --data '{"name":"Dogs"}' http://0.0.0.0:8000/specialty/
curl --request POST --data '{"name":"Cats"}' http://0.0.0.0:8000/specialty/
curl --request POST --data '{"name":"Pandas"}' http://0.0.0.0:8000/specialty/
```

##### Create Veterinarians
```sh
# We can create vet who is also a owner
curl --request POST --data '{"name":"Pablo", "specialties": ["Dogs", "Cats"], "owner_id": "b60bbdda-6aae-4b82-9711-5743b3667334"}' http://0.0.0.0:8000/vet/
# We can create vets who are not owners
curl --request POST --data '{"name":"Vince", "specialties": ["Exotic"]}' http://0.0.0.0:8000/vet/
curl --request POST --data '{"name":"Matt"}' http://0.0.0.0:8000/vet/

# Trying to add a new vet with an already associated owner id will cause integrity error
curl --request POST --data '{"name":"Jenny", "owner_id": "b60bbdda-6aae-4b82-9711-5743b3667334"}' http://0.0.0.0:8000/vet/

# Deleting the owner will lead to updating of owner field in vet to Null.
curl --request DELETE  http://0.0.0.0:8000/owner/b60bbdda-6aae-4b82-9711-5743b3667334

curl --request GET http://0.0.0.0:8000/vet/603e44b1-cf3a-4180-8df3-2c73fac507bd
```
