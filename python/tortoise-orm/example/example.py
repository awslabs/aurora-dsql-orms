# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncio
from datetime import date

from dotenv import load_dotenv
from tortoise import Tortoise, connections

from .models import Owner, Pet, Specialty, Vet
from .tortoise_config import TORTOISE_ORM

load_dotenv()


async def main():
    await init_db()
    await create_tables()
    await insert_sample_data()
    await query_data()


async def init_db():
    await Tortoise.init(config=TORTOISE_ORM, _create_db=False)
    print("Tortoise initialized successfully")


async def create_tables():
    await Tortoise.generate_schemas()
    print("Tables created successfully")


async def insert_sample_data():
    # Clear existing data.
    await Vet.all().delete()
    await Pet.all().delete()
    await Owner.all().delete()
    await Specialty.all().delete()

    owner1 = await Owner.create(name="John Doe", city="Seattle", telephone="555-1234")
    owner2 = await Owner.create(name="Jane Smith", city="Portland", telephone="555-5678")

    await Pet.create(name="Buddy", birth_date=date(2020, 5, 15), owner=owner1)
    await Pet.create(name="Whiskers", birth_date=date(2019, 8, 22), owner=owner2)

    cardiology = await Specialty.create(name="Cardiology")
    surgery = await Specialty.create(name="Surgery")

    vet1 = await Vet.create(name="Dr. Wilson")
    await vet1.specialties.add(cardiology, surgery)

    print("Sample data inserted successfully")


async def query_data():
    print("\n=== Basic Queries ===")

    # Count operations.
    owner_count = await Owner.all().count()
    pet_count = await Pet.all().count()
    print(f"Total owners: {owner_count}, Total pets: {pet_count}")

    # Filter operations.
    seattle_owners = await Owner.filter(city="Seattle")
    print(f"Seattle owners: {[o.name for o in seattle_owners]}")

    john = await Owner.get(name="John Doe")
    print(f"Found owner: {john.name} from {john.city}")

    print("\n=== Owners and their pets ===")
    owners = await Owner.all().prefetch_related("pets")

    for owner in owners:
        print(f"Owner: {owner.name} from {owner.city}")
        if hasattr(owner, "email") and owner.email:
            print(f"  Email: {owner.email}")
        for pet in owner.pets:
            print(f"  Pet: {pet.name} (born {pet.birth_date})")

    print("\n=== Vets and their specialties ===")
    vets = await Vet.all().prefetch_related("specialties")

    for vet in vets:
        specialties = [s.name for s in vet.specialties]
        print(f"Vet: {vet.name}, Specialties: {', '.join(specialties)}")

    print("\n=== Other Operations ===")

    # Values and values_list.
    owner_names = await Owner.all().values_list("name", flat=True)
    print(f"All owner names: {list(owner_names)}")

    # Update operations.
    owner = seattle_owners[0]
    if hasattr(owner, "email"):
        owner.email = f"{owner.name.lower().replace(' ', '.')}@example.com"
        await owner.save()
        print(f"Updated {owner.name}'s email")


def run_async(coroutine):
    """Simple async runner that cleans up DB connections on exit."""
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(coroutine)
    finally:
        loop.run_until_complete(connections.close_all(discard=True))


def run():
    run_async(main())


if __name__ == "__main__":
    run()
