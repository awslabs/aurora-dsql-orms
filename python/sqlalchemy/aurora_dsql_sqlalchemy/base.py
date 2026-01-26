# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from functools import lru_cache

from sqlalchemy import bindparam, select, sql
from sqlalchemy.dialects.postgresql import pg_catalog
from sqlalchemy.dialects.postgresql.base import PGDDLCompiler, PGDialect
from sqlalchemy.schema import ForeignKeyConstraint, PrimaryKeyConstraint
from sqlalchemy.sql import expression


class AuroraDSQLDDLCompiler(PGDDLCompiler):
    dialect: "AuroraDSQLDialect"

    def create_table_constraints(
        self, table, _include_foreign_key_constraints=None, **kw
    ):
        """
        modified from https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_0_41/lib/sqlalchemy/sql/compiler.py
        """

        constraints = []
        if table.primary_key:
            constraints.append(table.primary_key)

        all_fkcs = table.foreign_key_constraints
        if _include_foreign_key_constraints is not None:
            omit_fkcs = all_fkcs.difference(_include_foreign_key_constraints)
        else:
            omit_fkcs = set()

        constraints.extend(
            [
                c
                for c in table._sorted_constraints
                if c is not table.primary_key and c not in omit_fkcs
            ]
        )

        constraints_without_fk = []
        for constraint in table.constraints:
            # Disable foreign key creation since DSQL
            # doesn't support foreign key
            if isinstance(constraint, ForeignKeyConstraint):
                pass
            # Skip empty primary key constraints
            elif (
                isinstance(constraint, PrimaryKeyConstraint) and not constraint.columns
            ):
                pass
            else:
                constraints_without_fk.append(constraint)

        constraints = constraints_without_fk

        return ", \n\t".join(
            p
            for p in (
                self.process(constraint)
                for constraint in constraints
                if (constraint._should_create_for_compiler(self))
                and (
                    not self.dialect.supports_alter
                    or not getattr(constraint, "use_alter", False)
                )
            )
            if p is not None
        )

    def visit_create_index(self, create, **kw):
        """
        modified from https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_0_41/lib/sqlalchemy/dialects/postgresql/base.py
        """
        preparer = self.preparer
        index = create.element
        self._verify_index_table(index)
        text = "CREATE "
        if index.unique:
            text += "UNIQUE "

        text += "INDEX "

        if self.dialect._supports_create_index_async:
            text += "ASYNC "

        if create.if_not_exists:
            text += "IF NOT EXISTS "

        index_name = self._prepared_index_name(index, include_schema=False)
        table_name = preparer.format_table(index.table)
        text += f"{index_name} ON {table_name} "

        text += "({})".format(
            ", ".join(
                [
                    self.sql_compiler.process(
                        (
                            expr.self_group()
                            if not isinstance(expr, expression.ColumnClause)
                            else expr
                        ),
                        include_table=False,
                        literal_binds=True,
                    )
                    for expr in index.expressions
                ]
            )
        )

        includeclause = index.dialect_options[self.dialect.name]["include"]
        if includeclause:
            inclusions = [
                index.table.c[col] if isinstance(col, str) else col
                for col in includeclause
            ]
            text += " INCLUDE ({})".format(
                ", ".join([preparer.quote(c.name) for c in inclusions])
            )

        nulls_not_distinct = index.dialect_options[self.dialect.name][
            "nulls_not_distinct"
        ]
        if nulls_not_distinct is True:
            text += " NULLS NOT DISTINCT"
        elif nulls_not_distinct is False:
            text += " NULLS DISTINCT"

        return text


class AuroraDSQLDialect(PGDialect):
    name = "auroradsql"
    default_schema_name = "public"

    ddl_compiler = AuroraDSQLDDLCompiler

    supports_sequences = False
    preexecute_autoincrement_sequences = False

    supports_alter = False
    supports_native_enum = False

    _supports_create_index_async = True

    @lru_cache
    def _columns_query(self, schema, has_filter_names, scope, kind):
        """
        modified from https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_0_41/lib/sqlalchemy/dialects/postgresql/base.py
        """

        # NOTE: the query with the default and identity options scalarx
        # subquery is faster than trying to use outer joins for them
        generated = (
            pg_catalog.pg_attribute.c.attgenerated.label("generated")
            if self.server_version_info is not None
            and self.server_version_info >= (12,)
            else sql.null().label("generated")
        )

        # the original code uses sql.func.json_build_object when server_version is
        # greater than version 10
        # json_build_object is not supported by Aurora DSQL
        # TODO: if json_build_object is supported in the future,
        # restore _columns_query function from original

        identity = sql.null().label("identity_options")

        # join lateral performs the same as scalar_subquery here
        default = (
            select(
                pg_catalog.pg_get_expr(
                    pg_catalog.pg_attrdef.c.adbin,
                    pg_catalog.pg_attrdef.c.adrelid,
                )
            )
            .select_from(pg_catalog.pg_attrdef)
            .where(
                pg_catalog.pg_attrdef.c.adrelid == pg_catalog.pg_attribute.c.attrelid,
                pg_catalog.pg_attrdef.c.adnum == pg_catalog.pg_attribute.c.attnum,
                pg_catalog.pg_attribute.c.atthasdef,
            )
            .correlate(pg_catalog.pg_attribute)
            .scalar_subquery()
            .label("default")
        )
        relkinds = self._kind_to_relkinds(kind)
        query = (
            select(
                pg_catalog.pg_attribute.c.attname.label("name"),
                pg_catalog.format_type(
                    pg_catalog.pg_attribute.c.atttypid,
                    pg_catalog.pg_attribute.c.atttypmod,
                ).label("format_type"),
                default,
                pg_catalog.pg_attribute.c.attnotnull.label("not_null"),
                pg_catalog.pg_class.c.relname.label("table_name"),
                pg_catalog.pg_description.c.description.label("comment"),
                generated,
                identity,
            )
            .select_from(pg_catalog.pg_class)
            # NOTE: postgresql support table with no user column, meaning
            # there is no row with pg_attribute.attnum > 0. use a left outer
            # join to avoid filtering these tables.
            .outerjoin(
                pg_catalog.pg_attribute,
                sql.and_(
                    pg_catalog.pg_class.c.oid == pg_catalog.pg_attribute.c.attrelid,
                    pg_catalog.pg_attribute.c.attnum > 0,
                    ~pg_catalog.pg_attribute.c.attisdropped,
                ),
            )
            .outerjoin(
                pg_catalog.pg_description,
                sql.and_(
                    pg_catalog.pg_description.c.objoid
                    == pg_catalog.pg_attribute.c.attrelid,
                    pg_catalog.pg_description.c.objsubid
                    == pg_catalog.pg_attribute.c.attnum,
                ),
            )
            .where(self._pg_class_relkind_condition(relkinds))
            .order_by(pg_catalog.pg_class.c.relname, pg_catalog.pg_attribute.c.attnum)
        )
        query = self._pg_class_filter_scope_schema(query, schema, scope=scope)
        if has_filter_names:
            query = query.where(
                pg_catalog.pg_class.c.relname.in_(bindparam("filter_names"))
            )
        return query
