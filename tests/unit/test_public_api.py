# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


def test_public_api():
    import aurora_dsql_tortoise

    assert set(aurora_dsql_tortoise.__all__) == {
        "register_backends",
        "register_asyncpg",
        "register_psycopg",
    }
