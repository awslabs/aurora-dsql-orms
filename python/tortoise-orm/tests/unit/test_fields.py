# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest

from aurora_dsql_tortoise.common import fields as dsql_fields


def test_custom_bigint_field_default_cache():
    """Test custom BigIntField uses default cache size."""
    field = dsql_fields.BigIntField(primary_key=True)
    sql = field.get_for_dialect("postgres", "GENERATED_SQL")
    assert "CACHE 65536" in sql


@pytest.mark.parametrize("cache_size", [1, 65536, 100000])
def test_custom_bigint_field_custom_cache(cache_size):
    """Test custom BigIntField accepts custom cache size."""
    field = dsql_fields.BigIntField(primary_key=True, sequence_cache_size=cache_size)
    sql = field.get_for_dialect("postgres", "GENERATED_SQL")
    assert f"CACHE {cache_size}" in sql
