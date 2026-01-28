# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

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
