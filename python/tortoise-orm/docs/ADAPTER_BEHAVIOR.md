# Adapter Behavior

This document describes how the Aurora DSQL adapter for Tortoise ORM modifies standard Tortoise behavior for Aurora DSQL compatibility. For details on Aurora DSQL SQL feature compatibility, see the [Aurora DSQL documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html).

## Foreign key relationships are ORM-only

**Behavior:** Foreign key relationships defined in Tortoise models work normally for ORM operations, but the adapter does not create foreign key constraints in the database.

**Impact:**
- `ForeignKeyField` relationships work for queries, joins, and prefetch operations
- Constraints are not enforced at the database level
- Applications should maintain referential integrity through application logic

**Why this is necessary:** Aurora DSQL does not support foreign key constraints.

## Indexes are created asynchronously

**Behavior:** The adapter uses `CREATE INDEX ASYNC` instead of `CREATE INDEX` for all index creation.

**Impact:**
- Index creation returns immediately without waiting for completion
- Indexes will not be available for queries until background creation finishes
- No change required in application code

**Why this is necessary:** Aurora DSQL requires the `ASYNC` keyword for index creation.

## DDL statements are executed individually

**Behavior:** When generating schemas or running migrations, the adapter splits SQL containing multiple DDL statements and executes each one separately.

**Impact:**
- Each DDL statement runs in its own implicit transaction
- No change required in application code

**Why this is necessary:** Aurora DSQL transactions can contain only one DDL statement. Attempting to run multiple DDL statements in a single transaction will fail.

## Aerich compatibility patches

When `aurora_dsql_tortoise.aerich_compat` is included in your models, the following patches are applied:

**UUID primary keys for Aerich model:** The internal Aerich model uses `UUID` instead of auto-increment integer for its primary key.

**TEXT instead of JSON:** The Aerich model's `content` field uses `TEXT` instead of `JSON`/`JSONB` column types.

**Individual DDL execution:** Migration files may contain multiple DDL statements. The compatibility module splits these and executes each statement separately, since DSQL transactions can only contain one DDL statement.

**Disabled transaction wrapping:** Generated migration files set `RUN_IN_TRANSACTION = False` since DSQL transactions cannot contain multiple DDL statements.
