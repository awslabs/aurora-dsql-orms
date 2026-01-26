# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from sqlalchemy import (
    Column,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    schema,
)
from sqlalchemy.testing import fixtures
from sqlalchemy.testing.assertions import AssertsCompiledSQL
from sqlalchemy.testing.config import combinations
from sqlalchemy.testing.util import resolve_lambda

from aurora_dsql_sqlalchemy.psycopg import AuroraDSQLDialect_psycopg
from aurora_dsql_sqlalchemy.psycopg2 import AuroraDSQLDialect_psycopg2

from .conftest import DRIVER


class CompileTest(fixtures.TestBase, AssertsCompiledSQL):
    """
    modified from https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_0_41/test/dialect/postgresql/test_compiler.py

    A SQL compiler test to check if the corresponding CREATE INDEX ASYNC SQL queries
    are correctly generated

    """

    __dialect__ = (
        AuroraDSQLDialect_psycopg2()
        if DRIVER == "psycopg2"
        else AuroraDSQLDialect_psycopg()
    )

    @combinations(
        (
            lambda tbl: schema.CreateIndex(
                Index(
                    "test_idx1",
                    tbl.c.data,
                    unique=True,
                    auroradsql_nulls_not_distinct=True,
                )
            ),
            "CREATE UNIQUE INDEX ASYNC test_idx1 ON test_tbl (data) NULLS NOT DISTINCT",
        ),
        (
            lambda tbl: schema.CreateIndex(
                Index(
                    "test_idx2",
                    tbl.c.data2,
                    unique=True,
                    auroradsql_nulls_not_distinct=False,
                )
            ),
            "CREATE UNIQUE INDEX ASYNC test_idx2 ON test_tbl (data2) NULLS DISTINCT",
        ),
        (
            lambda tbl: schema.CreateIndex(
                Index(
                    "test_idx3",
                    tbl.c.data3,
                    unique=True,
                )
            ),
            "CREATE UNIQUE INDEX ASYNC test_idx3 ON test_tbl (data3)",
        ),
    )
    def test_nulls_not_distinct(self, expr_fn, expected):
        dd = self.__dialect__
        m = MetaData()
        tbl = Table(
            "test_tbl",
            m,
            Column("data", String),
            Column("data2", Integer),
            Column("data3", Integer),
        )

        expr = resolve_lambda(expr_fn, tbl=tbl)
        self.assert_compile(expr, expected, dialect=dd)

    def test_index_extra_include_1(self):
        metadata = MetaData()
        tbl = Table(
            "test",
            metadata,
            Column("x", Integer),
            Column("y", Integer),
            Column("z", Integer),
        )
        idx = Index("foo", tbl.c.x, auroradsql_include=["y"])
        self.assert_compile(
            schema.CreateIndex(idx),
            "CREATE INDEX ASYNC foo ON test (x) INCLUDE (y)",
            dialect=self.__dialect__,
        )

    def test_index_extra_include_2(self):
        metadata = MetaData()
        tbl = Table(
            "test",
            metadata,
            Column("x", Integer),
            Column("y", Integer),
            Column("z", Integer),
        )
        idx = Index("foo", tbl.c.x, auroradsql_include=[tbl.c.y])
        self.assert_compile(
            schema.CreateIndex(idx),
            "CREATE INDEX ASYNC foo ON test (x) INCLUDE (y)",
            dialect=self.__dialect__,
        )
