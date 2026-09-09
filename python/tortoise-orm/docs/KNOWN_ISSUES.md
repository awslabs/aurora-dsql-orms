# Known Issues

This document tracks known issues when using the Aurora DSQL adapter for Tortoise ORM. For Aurora DSQL SQL compatibility details, see the [Aurora DSQL documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html).

## Nested transactions

**Issue:** Nested `in_transaction()` or `atomic()` blocks fail.

**Why:** Tortoise ORM uses savepoints to implement nested transaction semantics.

**Workaround:** Restructure code to avoid nested transactions.

## Aerich compatibility module prevents side-by-side PostgreSQL use

**Issue:** Enabling the Aerich compatibility module (`aurora_dsql_tortoise.aerich_compat`) prevents using standard PostgreSQL and Aurora DSQL in the same application.

**Why:** The compatibility module patches global Aerich behavior to use DSQL-compatible DDL generation. These patches affect all database connections, not just DSQL connections.

**Workaround:** If you need to use both PostgreSQL and Aurora DSQL in the same application, do not include `aurora_dsql_tortoise.aerich_compat` in your models list. You will need to manage DSQL migrations manually.
