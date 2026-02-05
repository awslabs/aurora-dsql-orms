# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from sqlalchemy import BigInteger, Column, Identity, Integer, String, Table, select
from sqlalchemy.exc import DataError
from sqlalchemy.testing import fixtures
from sqlalchemy.testing.assertions import eq_


class SerialPrimaryKeyTest(fixtures.TestBase):
    """Test that serial primary key with autoincrement works"""

    __backend__ = True

    @pytest.mark.parametrize("cache_size", [65536, 200000, 1])
    def test_serial_autoincrement(self, connection, metadata, cache_size):
        t = Table(
            "serial_test",
            metadata,
            Column("id", BigInteger, Identity(always=True, cache=cache_size), primary_key=True),
            Column("name", String(50)),
        )

        t.create(connection)
        connection.commit()
        connection.begin()

        connection.execute(t.insert().values(name="first"))
        connection.execute(t.insert().values(name="second"))
        connection.commit()

        stmt = select(t).order_by(t.c.id)
        rows = connection.execute(stmt).fetchall()

        eq_(len(rows), 2)
        eq_(rows[0].name, "first")
        eq_(rows[1].name, "second")

    def test_autoincrement_with_integer(self, connection, metadata):
        """Test that autoincrement=True on Integer primary key works"""
        t = Table(
            "autoincrement_test",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(50)),
        )

        t.create(connection)
        connection.commit()
        connection.begin()

        connection.execute(t.insert().values(name="first"))
        connection.execute(t.insert().values(name="second"))
        connection.commit()

        stmt = select(t).order_by(t.c.id)
        rows = connection.execute(stmt).fetchall()

        eq_(len(rows), 2)
        eq_(rows[0].name, "first")
        eq_(rows[1].name, "second")

    def test_implicit_autoincrement(self, connection, metadata):
        """Test that implicit autoincrement on Integer primary key works"""
        t = Table(
            "implicit_test",
            metadata,
            Column("id", Integer, primary_key=True),  # autoincrement implicit
            Column("name", String(50)),
        )

        t.create(connection)
        connection.commit()
        connection.begin()

        connection.execute(t.insert().values(name="first"))
        connection.execute(t.insert().values(name="second"))
        connection.commit()

        stmt = select(t).order_by(t.c.id)
        rows = connection.execute(stmt).fetchall()

        eq_(len(rows), 2)
        eq_(rows[0].name, "first")
        eq_(rows[1].name, "second")

    @pytest.mark.parametrize("invalid_cache", [2, 1000, 65535])
    def test_invalid_cache_size(self, connection, metadata, invalid_cache):
        """Test that invalid cache size raises DataError"""
        t = Table(
            "invalid_cache_test",
            metadata,
            Column("id", BigInteger, Identity(always=True, cache=invalid_cache), primary_key=True),
            Column("name", String(50)),
        )

        with pytest.raises(DataError, match="CACHE.*must be greater than or equal to.*65536.*or equal to 1"):
            t.create(connection)
