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

"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from pet_clinic.views import OwnerView, PetView, SpecialtyView, VetSpecialtiesView, VetView

urlpatterns = [
    path("owner/", OwnerView.as_view(), name="owner"),
    path("owner/<id>", OwnerView.as_view(), name="owner"),
    path("pet/", PetView.as_view(), name="pet"),
    path("pet/<id>", PetView.as_view(), name="pet"),
    path("vet/", VetView.as_view(), name="vet"),
    path("vet/<id>", VetView.as_view(), name="vet"),
    path("specialty/", SpecialtyView.as_view(), name="specialty"),
    path("specialty/<name>", SpecialtyView.as_view(), name="specialty"),
    path("vet-specialties/", VetSpecialtiesView.as_view(), name="vet-specialties"),
]
