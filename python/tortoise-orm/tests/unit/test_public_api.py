# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import importlib
import sys
from unittest.mock import patch

import pytest


def test_public_api():
    import aurora_dsql_tortoise

    assert set(aurora_dsql_tortoise.__all__) == {
        "register_backends",
        "register_asyncpg",
        "register_psycopg",
    }


BACKENDS = {
    "asyncpg": "register_asyncpg",
    "psycopg": "register_psycopg",
}


@pytest.mark.parametrize("backend", BACKENDS.keys())
def test_import_doesnt_require_other_backend(subtests, backend):
    """Test that importing the dsql client doesn't require unneeded dependencies from the other backend."""
    # We run the entire import tree while pretending that psycopg isn't installed
    other_backends = {b for b in BACKENDS.keys() if b != backend}
    no_other_backends = {
        k: None
        for k in sys.modules.keys() 
        for other in other_backends
        if k.startswith(other)
    }
    evict_dsql = {k for k in sys.modules.keys() if k.startswith("aurora_dsql_tortoise")}

    with patch.dict(sys.modules, no_other_backends) as mods:
        for mod in evict_dsql:
            mods.pop(mod, None)

        with subtests.test(f"Importing root module for {backend} doesn't require {other_backends}"):
            root = importlib.import_module("aurora_dsql_tortoise")
            root = importlib.reload(root) # Test: No dependency at import time

        with subtests.test(f"Registering {backend} backend doesn't require {other_backends}"):
            getattr(root, BACKENDS[backend])()

        with subtests.test(f"Importing {backend} engine module doesn't require {other_backends}"):
            engine_mod = importlib.import_module(f"aurora_dsql_tortoise.{backend}")
            engine_mod = importlib.reload(engine_mod)
