# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_mock_engine,
    schema,
)
from sqlalchemy.exc import CompileError
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

    def test_add_check_constraint_is_not_valid(self):
        # DSQL rejects a plain ALTER TABLE ADD CONSTRAINT ... CHECK; it must be
        # added NOT VALID, then validated asynchronously as a separate step.
        metadata = MetaData()
        tbl = Table("test_tbl", metadata, Column("qty", Integer))
        ck = CheckConstraint("qty >= 0", name="ck_qty", table=tbl)
        self.assert_compile(
            schema.AddConstraint(ck),
            "ALTER TABLE test_tbl ADD CONSTRAINT ck_qty CHECK (qty >= 0) NOT VALID",
            dialect=self.__dialect__,
        )

    def test_add_non_check_constraint_gets_no_not_valid(self):
        # Guard: the NOT VALID suffix is CHECK/FK-specific. DSQL does not
        # support adding UNIQUE constraints via ALTER TABLE.
        metadata = MetaData()
        tbl = Table("test_tbl", metadata, Column("data", String))
        uq = UniqueConstraint(tbl.c.data, name="uq_data")
        compiled = str(schema.AddConstraint(uq).compile(dialect=self.__dialect__))
        assert "NOT VALID" not in compiled

    def test_supports_alter_for_foreign_key_ordering(self):
        assert self.__dialect__.supports_alter is True

    def _capture_metadata_ddl(self, metadata, operation):
        statements = []

        def capture(ddl, *args, **kwargs):
            statements.append(
                " ".join(str(ddl.compile(dialect=engine.dialect)).split())
            )

        engine = create_mock_engine(f"auroradsql+{DRIVER}://", capture)
        getattr(metadata, operation)(engine, checkfirst=False)
        return statements

    def _assert_fk_only_metadata_alters(
        self,
        metadata,
        expected_adds,
        expected_drops,
    ):
        create_statements = self._capture_metadata_ddl(metadata, "create_all")
        create_alters = {
            statement
            for statement in create_statements
            if statement.startswith("ALTER TABLE")
        }

        assert create_alters == expected_adds
        assert any(
            statement.startswith("CREATE TABLE") and "PRIMARY KEY" in statement
            for statement in create_statements
        )
        assert any(
            statement.startswith("CREATE TABLE") and "UNIQUE" in statement
            for statement in create_statements
        )
        assert all(
            "UNIQUE" not in statement and "PRIMARY KEY" not in statement
            for statement in create_alters
        )

        drop_statements = self._capture_metadata_ddl(metadata, "drop_all")
        drop_alters = {
            statement
            for statement in drop_statements
            if statement.startswith("ALTER TABLE")
        }
        assert drop_alters == expected_drops

    def test_create_all_drop_all_cyclic_foreign_keys_use_fk_only_alters(self):
        metadata = MetaData()
        left = Table(
            "left_table",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("right_id", Integer),
            UniqueConstraint("right_id", name="uq_left_right"),
        )
        right = Table(
            "right_table",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("left_id", Integer),
            UniqueConstraint("left_id", name="uq_right_left"),
        )
        left.append_constraint(
            ForeignKeyConstraint(
                ["right_id"],
                ["right_table.id"],
                name="fk_left_right",
            )
        )
        right.append_constraint(
            ForeignKeyConstraint(
                ["left_id"],
                ["left_table.id"],
                name="fk_right_left",
            )
        )

        self._assert_fk_only_metadata_alters(
            metadata,
            {
                "ALTER TABLE left_table ADD CONSTRAINT fk_left_right "
                "FOREIGN KEY(right_id) REFERENCES right_table (id) NOT VALID",
                "ALTER TABLE right_table ADD CONSTRAINT fk_right_left "
                "FOREIGN KEY(left_id) REFERENCES left_table (id) NOT VALID",
            },
            {
                "ALTER TABLE left_table DROP CONSTRAINT fk_left_right",
                "ALTER TABLE right_table DROP CONSTRAINT fk_right_left",
            },
        )

    def test_create_all_drop_all_use_alter_foreign_key_is_fk_only_alter(self):
        metadata = MetaData()
        Table(
            "parent",
            metadata,
            Column("id", Integer, primary_key=True),
        )
        child = Table(
            "child",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("parent_id", Integer),
            UniqueConstraint("parent_id", name="uq_child_parent"),
        )
        child.append_constraint(
            ForeignKeyConstraint(
                ["parent_id"],
                ["parent.id"],
                name="fk_child_parent",
                use_alter=True,
            )
        )

        self._assert_fk_only_metadata_alters(
            metadata,
            {
                "ALTER TABLE child ADD CONSTRAINT fk_child_parent "
                "FOREIGN KEY(parent_id) REFERENCES parent (id) NOT VALID",
            },
            {
                "ALTER TABLE child DROP CONSTRAINT fk_child_parent",
            },
        )

    def test_inline_foreign_key(self):
        metadata = MetaData()
        Table("parent", metadata, Column("id", Integer, primary_key=True))
        child = Table(
            "child",
            metadata,
            Column("id", Integer, primary_key=True),
            Column(
                "parent_id",
                Integer,
                ForeignKey(
                    "parent.id",
                    ondelete="RESTRICT",
                    onupdate="NO ACTION",
                ),
            ),
        )

        self.assert_compile(
            schema.CreateTable(child),
            "CREATE TABLE child ("
            "id BIGINT NOT NULL GENERATED BY DEFAULT AS IDENTITY (CACHE 65536), "
            "parent_id INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(parent_id) REFERENCES parent (id) "
            "ON DELETE RESTRICT ON UPDATE NO ACTION"
            ")",
            dialect=self.__dialect__,
        )

    def test_supported_foreign_key_actions(self):
        metadata = MetaData()
        Table("parent", metadata, Column("id", Integer, primary_key=True))
        child = Table(
            "child",
            metadata,
            Column(
                "parent_id",
                Integer,
                ForeignKey(
                    "parent.id",
                    ondelete="CASCADE",
                    onupdate="SET NULL",
                    deferrable=True,
                    initially="DEFERRED",
                ),
            ),
        )

        compiled = str(schema.CreateTable(child).compile(dialect=self.__dialect__))
        assert "ON DELETE CASCADE" in compiled
        assert "ON UPDATE SET NULL" in compiled
        assert "DEFERRABLE INITIALLY DEFERRED" in compiled

    def test_add_foreign_key_constraint_is_not_valid(self):
        metadata = MetaData()
        Table("parent", metadata, Column("id", Integer, primary_key=True))
        child = Table(
            "child",
            metadata,
            Column("parent_id", Integer),
            ForeignKeyConstraint(["parent_id"], ["parent.id"], name="fk_parent"),
        )
        constraint = next(iter(child.foreign_key_constraints))

        self.assert_compile(
            schema.AddConstraint(constraint),
            "ALTER TABLE child ADD CONSTRAINT fk_parent FOREIGN KEY(parent_id) "
            "REFERENCES parent (id) NOT VALID",
            dialect=self.__dialect__,
        )

    def test_existing_postgresql_not_valid_is_not_duplicated(self):
        metadata = MetaData()
        Table("parent", metadata, Column("id", Integer, primary_key=True))
        child = Table(
            "child",
            metadata,
            Column("parent_id", Integer),
            ForeignKeyConstraint(
                ["parent_id"],
                ["parent.id"],
                name="fk_parent",
                postgresql_not_valid=True,
            ),
        )
        constraint = next(iter(child.foreign_key_constraints))

        compiled = str(
            schema.AddConstraint(constraint).compile(dialect=self.__dialect__)
        )
        assert compiled.count("NOT VALID") == 1

    def test_drop_foreign_key_constraint(self):
        metadata = MetaData()
        Table("parent", metadata, Column("id", Integer, primary_key=True))
        child = Table(
            "child",
            metadata,
            Column("parent_id", Integer),
            ForeignKeyConstraint(
                ["parent_id"],
                ["parent.id"],
                name="fk_parent",
            ),
        )
        constraint = next(iter(child.foreign_key_constraints))

        self.assert_compile(
            schema.DropConstraint(constraint),
            "ALTER TABLE child DROP CONSTRAINT fk_parent",
            dialect=self.__dialect__,
        )

    def test_match_partial_foreign_key(self):
        metadata = MetaData()
        Table("parent", metadata, Column("id", Integer, primary_key=True))
        child = Table(
            "child",
            metadata,
            Column("parent_id", Integer),
            ForeignKeyConstraint(
                ["parent_id"],
                ["parent.id"],
                match="PARTIAL",
            ),
        )

        with pytest.raises(
            CompileError,
            match="PostgreSQL does not implement MATCH PARTIAL",
        ):
            schema.CreateTable(child).compile(dialect=self.__dialect__)
