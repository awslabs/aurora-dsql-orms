# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from src.example import (
    create_dsql_engine,
    demo_pet_clinic_operations,
    demo_retry_mechanism,
)


# Smoke tests that our example works fine
def test_example():
    try:
        engine = create_dsql_engine()
        demo_pet_clinic_operations(engine)
        demo_retry_mechanism(engine)
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")
