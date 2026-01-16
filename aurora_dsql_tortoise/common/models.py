# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from tortoise.models import Model
from tortoise.transactions import in_transaction
from typing_extensions import Self


class DSQLModel(Model):
    """Base model that overrides methods which are incompatible with DSQL."""

    class Meta:
        abstract = True

    @classmethod
    async def update_or_create(
        cls: type[Self],
        defaults: dict | None = None,
        using_db=None,
        **kwargs: Any,
    ) -> tuple[Self, bool]:
        """DSQL-compatible update_or_create using OCC instead of SELECT FOR UPDATE."""
        # This code is based on Tortoise ORM
        # Copyright (c) Andrey Bondar & Nickolas Grigoriadis & long2ice
        # Modifications: Copyright (c) Amazon.com, Inc. or its affiliates.
        # License to Modifications: Apache 2.0
        # Source: https://github.com/tortoise/tortoise-orm/blob/1d2400bb3daff7b1aa34884062ca0e936ea214b2/tortoise/models.py#L1165
        if not defaults:
            defaults = {}
        db = using_db or cls._choose_db(True)
        async with in_transaction(connection_name=db.connection_name) as connection:
            # Change is here, replaced select_for_update() with filter call to get QuerySet.
            instance = await cls.filter(**kwargs).using_db(connection).get_or_none(**kwargs)
            if instance:
                await instance.update_from_dict(defaults).save(using_db=connection)
                return instance, False
        return await cls._create_or_get(db, defaults, **kwargs)
