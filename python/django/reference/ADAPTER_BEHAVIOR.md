# Behavior of Aurora DSQL Adapter for Django

This document describes how the Aurora DSQL adapter for Django modifies standard Django behavior for Aurora DSQL compatibility. For details on Aurora DSQL SQL compatibility, see the [Aurora DSQL documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html).


## AutoField and Primary Key Behavior

**Behavior:** The Aurora DSQL adapter for Django automatically converts Django's `AutoField` and `BigAutoField` to use UUID primary keys instead of auto-incrementing integers. Applications requiring sequential integer keys can override this by setting `USE_SEQUENCE_AUTOFIELDS=True`.

**Impact:**
- All primary keys will be UUIDs by default (e.g. `8fcc0dd2-1d96-4428-a619-f0e43996dc19`) instead of integers (e.g. `1`, `2`, `3`)
- Sort order may not match insertion order
- URLs, session data, etc. may contain UUID strings
- The `SequenceAutoField` can be used in custom models for explicit sequence-based IDs with per-model cache size configuration

**Limitations:** Not all Django `contrib` apps are compatible with UUID primary keys. For new applications, customers are encouraged to use `UUIDField` directly instead of `AutoField` where possible.

**Sequence Configuration:**

```python
DATABASES = {
    "default": {
        # Other database settings
        "ENGINE": "aurora_dsql_django",
        "USE_SEQUENCE_AUTOFIELDS": True, # Optional, False by default
        "SEQUENCE_CACHE_SIZE": 65536, # Optional, 65536 by default
        "OPTIONS": {
            "sslmode": "require"
        },
    },
}
```

**Usage for individual models:**

```python
from aurora_dsql_django import SequenceAutoField

class Owner(models.Model):
    id = SequenceAutoField(primary_key=True)
    name = models.CharField(max_length=30, blank=False)
```

See the [Working with sequences and identity columns](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/sequences-identity-columns-working-with.html) page for more details.

## Server-side cursors automatically disabled

**Behavior:** The Aurora DSQL adapter for Django automatically sets `DISABLE_SERVER_SIDE_CURSORS = True` for database connections unless otherwise configured.

**Impact:** Large querysets will load entirely into memory instead of streaming, which may affect memory usage for large datasets.

**DSQL feature:** [SQL compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)

## Foreign key constraints are skipped during migrations

**Behavior:** The Aurora DSQL adapter for Django automatically skips foreign key constraint creation and removal operations during migrations.

**Impact:** 
- Foreign key constraints are not enforced at the database level
- Applications must maintain referential integrity through Django model validation and application logic
- Existing migrations from other databases will continue to work without modification

**DSQL feature:** [SQL compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)

## Check constraints on existing tables are validated asynchronously

**Behavior:** The Aurora DSQL adapter for Django supports `CHECK` constraints both inline at `CREATE TABLE` and added to existing tables during migrations. Because DSQL requires `CHECK` constraints on an existing table to be added with `NOT VALID`, the adapter emits two statements when adding a constraint: `ALTER TABLE ... ADD CONSTRAINT ... CHECK (...) NOT VALID`, followed by `ALTER TABLE ASYNC ... VALIDATE CONSTRAINT ...`.

**Impact:**
- The constraint is enforced on all new inserts and updates as soon as the migration completes.
- Validation of rows that already exist in the table runs as an asynchronous DSQL DDL job (returns a `job_id`); the migration does not block until it finishes.
- If existing rows violate the constraint, the validation job fails and the constraint remains in the `NOT VALID` state (still enforced for new writes, but not marked valid for existing data). Track the outcome via the `sys.jobs` system view and fix offending rows before re-running validation. Migrations that add a constraint to a table with known-clean data are unaffected.

**DSQL feature:** [ALTER TABLE syntax](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-supported-sql-subsets.html#alter-table-syntax-support)

## Expression indexes are skipped during migrations

**Behavior:** The Aurora DSQL adapter for Django automatically skips creation and removal of expression indexes during migrations.

**Impact:**
- Expression indexes (e.g., `Index(Upper('name'))`) are not created during migration operations
- Query performance may be affected for queries that would benefit from expression indexes
- Existing migrations containing expression indexes will execute without errors

**DSQL feature:** [SQL compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
