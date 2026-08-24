# Django migrations on Aurora DSQL

Use Django's normal `makemigrations` and `migrate` workflow. Before applying a
migration, generate its SQL and check it with
[`dsql-lint`](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint):

```bash
python manage.py sqlmigrate <app> <migration> | uvx dsql-lint -
```

Alternatively, install the current CLI with `pip install --upgrade dsql-lint`
and replace `uvx dsql-lint` with `dsql-lint`. A clean result needs no
DSQL-specific migration steps. If the linter reports an error, follow its
suggested rewrite and lint the revised SQL again before applying it.

The operations that commonly require intervention are:

- Field type changes, including `max_length`, because Django emits
  `ALTER COLUMN ... TYPE`.
- Changing a nullable field to non-nullable because Django emits
  `ALTER COLUMN ... SET NOT NULL`.
- Adding a field with an inline `DEFAULT` or `NOT NULL` constraint.

Use an explicit staged migration or planned table recreation for these
operations. Keep Django's model state synchronized with manual SQL by using
`SeparateDatabaseAndState` or `RunSQL(..., state_operations=[...])`.

Avoid using `migrate --fake` as the normal workflow. Reserve it for recovery
after manually verifying that the database schema exactly matches the state
expected by the migration.

## Migration safety

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

Test forward and reverse migrations on a disposable DSQL cluster containing
representative data. Monitor asynchronous index builds and constraint
validation through `sys.jobs` before relying on them.
