# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import pytest
from sqlalchemy import (
    BIGINT,
    DECIMAL,
    Column,
    Integer,
    Sequence,
    String,
    Table,
    select,
    text,
)
from sqlalchemy.schema import CreateSequence
from sqlalchemy.testing import fixtures
from sqlalchemy.testing.assertions import eq_


class SequenceTest(fixtures.TestBase):
    __backend__ = True

    def _cleanup_sequence(self, connection, sequence_name):
        """Helper to drop a sequence with CASCADE"""
        try:
            connection.execute(text(f"DROP SEQUENCE IF EXISTS {sequence_name} CASCADE"))
            connection.commit()
        except Exception:
            connection.rollback()

    def test_int_seq(self, connection, metadata):
        """
        Test Integer sequence - dialect converts Integer to BIGINT
        for DSQL compatibility
        """
        seq = Sequence("int_seq", data_type=Integer(), metadata=metadata)

        t = Table(
            "int_seq_t",
            metadata,
            Column("id", Integer, seq),
            Column("txt", String(50)),
        )
        t.create(connection, checkfirst=False)
        connection.commit()
        connection.begin()

        connection.execute(t.insert().values({"txt": "int_seq test"}))
        connection.commit()

        result = connection.execute(select(t)).first()
        eq_(result.id, 1)

    def test_int_seq_order(self, connection, metadata):
        """Test that sequence generates sequential IDs for multiple inserts"""
        seq = Sequence("test_order_seq", metadata=metadata)

        # Create table (sequence will be created automatically)
        t = Table(
            "sequence_test",
            metadata,
            Column("id", Integer, seq, primary_key=True),
            Column("name", String(50)),
        )
        t.create(connection, checkfirst=False)
        connection.commit()
        connection.begin()

        connection.execute(t.insert().values(name="first"))
        connection.execute(t.insert().values(name="second"))
        connection.execute(t.insert().values(name="third"))
        connection.commit()

        stmt = select(t).order_by(t.c.id)
        rows = connection.execute(stmt).fetchall()

        eq_(len(rows), 3)
        eq_(rows[0].name, "first")
        eq_(rows[1].name, "second")
        eq_(rows[2].name, "third")

    def test_int_seq_with_start(self, connection, metadata):
        seq = Sequence("id_start", data_type=Integer(), start=42, metadata=metadata)

        t = Table(
            "int_seq_start_t",
            metadata,
            Column("id", Integer, seq),
            Column("txt", String(50)),
        )
        t.create(connection, checkfirst=False)
        connection.commit()
        connection.begin()

        connection.execute(t.insert().values({"txt": "start test"}))
        connection.commit()

        result = connection.execute(select(t)).first()
        eq_(result.id, 42)

    @pytest.mark.parametrize("optional", [True, False])
    def test_bigint_seq_with_optional(self, connection, metadata, optional, request):
        sequence_name = "bigint_seq"

        if optional:
            request.addfinalizer(
                lambda: self._cleanup_sequence(connection, sequence_name)
            )

        seq = Sequence(
            sequence_name, start=3000000000, optional=optional, metadata=metadata
        )

        if optional:
            connection.execute(CreateSequence(seq))
            connection.commit()

        t = Table(
            "bigint_seq_t",
            metadata,
            Column("id", BIGINT, seq),
            Column("txt", String(50)),
        )
        t.create(connection, checkfirst=False)
        connection.commit()
        connection.begin()

        connection.execute(t.insert().values({"txt": "bigint_seq test"}))
        connection.commit()

        result = connection.scalar(select(t.c.id))
        eq_(result, 3000000000)

    def test_bigint_seq_direct(self, connection, metadata):
        t = Table(
            "bigint_seq_direct_t",
            metadata,
            Column(
                "id", BIGINT, default=Sequence("bigint_direct_seq", start=3000000000)
            ),
            Column("txt", String(50)),
        )
        t.create(connection, checkfirst=False)
        connection.commit()
        connection.begin()

        connection.execute(t.insert().values({"txt": "bigint_seq_direct_t test"}))
        connection.commit()

        result = connection.scalar(select(t.c.id))
        eq_(result, 3000000000)

    def test_bigint_seq_direct_with_cache(self, connection, metadata):
        t = Table(
            "bigint_seq_direct_t",
            metadata,
            Column(
                "id",
                BIGINT,
                default=Sequence("bigint_direct_seq", start=1, cache=100000),
            ),
            Column("txt", String(50)),
        )
        t.create(connection, checkfirst=False)
        connection.commit()
        connection.begin()

        connection.execute(t.insert().values({"txt": "bigint_seq_direct_t test"}))
        connection.commit()

        result = connection.scalar(select(t.c.id))
        eq_(result, 1)

    def test_unsupported_decimal_seq(self, connection, metadata):
        """Test that DECIMAL sequence type raises DataError"""
        from sqlalchemy.exc import DataError

        seq = Sequence("decimal_seq", data_type=DECIMAL(10, 0), metadata=metadata)

        t = Table(
            "decimal_seq_t",
            metadata,
            Column("id", DECIMAL(10, 0), seq),
            Column("txt", String(50)),
        )

        with pytest.raises(DataError, match="sequence type must be bigint"):
            t.create(connection, checkfirst=False)
