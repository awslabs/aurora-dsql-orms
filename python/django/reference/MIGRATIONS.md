# Django migrations on Aurora DSQL

Use Django's normal `makemigrations` and `migrate` workflow, but review and test
the generated SQL against Aurora DSQL. The adapter uses Django's PostgreSQL
schema editor and overrides the operations that need DSQL-specific syntax.

## Schema operation support

The following table covers the operations most likely to appear in field
migrations. Check the current
[Aurora DSQL `ALTER TABLE` documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/alter-table-syntax-support.html)
for the complete syntax.

| Django operation | Aurora DSQL behavior |
| --- | --- |
| `RemoveField` | Uses native `ALTER TABLE ... DROP COLUMN ... CASCADE` |
| `AlterField(null=True)` | Uses native `ALTER COLUMN ... DROP NOT NULL` |
| Set or remove a database default | Supported natively |
| Rename a field or model | Supported natively |
| Add a nullable field without a database default | Supported natively |
| Change a field's database type, including `max_length` | Not supported; Django emits `ALTER COLUMN ... TYPE` |
| `AlterField(null=False)` | Not supported; DSQL doesn't support `SET NOT NULL` |
| Add a field with inline constraints or a database default | May require a staged migration because DSQL's `ADD COLUMN` syntax is limited |

`RemoveField` is destructive. Django's PostgreSQL schema editor includes
`CASCADE`, so dependent views and other objects can also be removed. Primary
key columns cannot be dropped. DSQL makes a dropped column invisible rather
than immediately reclaiming its storage, and the column still counts toward
the table's lifetime column limit.

## Recommended workflow

1. Generate migrations with `python manage.py makemigrations`.
2. Inspect them with `python manage.py sqlmigrate <app> <migration>`.
3. Test both forwards and backwards migration paths on a disposable DSQL
   cluster containing representative data.
4. Run `python manage.py migrate --plan` before applying the migration.
5. For zero-downtime changes, deploy code compatible with both schemas before
   applying a destructive migration.
6. Monitor asynchronous index builds and constraint validation through
   `sys.jobs` before relying on them.

The adapter declares `can_rollback_ddl = False`, so schema changes aren't
wrapped in a rollback-capable transaction. Keep schema migrations small,
prefer one non-idempotent schema operation per migration, and don't place
schema editor calls inside `transaction.atomic()`. A failed migration may
leave an earlier operation applied even though Django didn't record the
migration as complete.

## Data migrations

Keep schema and data changes in separate migrations. Use historical models
from the `apps` argument in `RunPython`, not imports from the current
application:

```python
def populate_value(apps, schema_editor):
    Widget = apps.get_model("inventory", "Widget")
    alias = schema_editor.connection.alias
    # Use one UPDATE only when the data fits within DSQL transaction limits.
    Widget.objects.using(alias).filter(new_value__isnull=True).update(new_value="")
```

For large updates, set `atomic = False` on the migration, process bounded
batches in their own transactions, and make each batch safe to retry. Keep
every batch within the current
[Aurora DSQL transaction limits](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html).

## Unsupported changes

For `ALTER COLUMN TYPE`, `SET NOT NULL`, or an unsupported `ADD COLUMN`
definition, use an explicit staged migration or a planned table recreation.
Keep Django's model state synchronized with manual SQL by using
`SeparateDatabaseAndState` or `RunSQL(..., state_operations=[...])`.

Avoid using `migrate --fake` as the normal workflow. Reserve it for recovery
after manually verifying that the database schema exactly matches the state
expected by the migration.
