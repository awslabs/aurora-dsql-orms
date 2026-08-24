# Known Issues

This document tracks known issues when using the Aurora DSQL adapter for Django. For Aurora DSQL SQL compatibility details, see the [Aurora DSQL documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html).

## Framework Issues

### Server-side cursors

**Issue:** Django admin and large querysets fail with:

```
NotSupportedError: unsupported statement: DeclareCursor
```

**Workaround:**

Add `'DISABLE_SERVER_SIDE_CURSORS': True` to your database `OPTIONS`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'aurora_dsql_django',
        'DISABLE_SERVER_SIDE_CURSORS': True,
        # ... other options
    }
}
```

This configuration is the default when using the Aurora DSQL adapter for Django, so removing any existing
`DISABLE_SERVER_SIDE_CURSORS`
configuration should configure the correct behavior.

### Django Sites Framework

**Issue:** Django's sites framework fails with:

```
django.db.utils.ProgrammingError: operator does not exist: uuid = integer
LINE 1: ...le.com', "name" = 'example.com' WHERE "django_site"."id" = 1
```

**Why:** The Aurora DSQL adapter for Django uses UUID for `AutoField`, but Django's sites framework hardcodes
`SITE_ID = 1` (integer) and expects integer primary keys.

**Workaround:** Remove `django.contrib.sites` from `INSTALLED_APPS` and avoid its use.

## Migration Issues

### ALTER COLUMN TYPE operations

**Issue:** Django migrations that change a field's database type fail with:

```
psycopg.errors.FeatureNotSupported:
    unsupported ALTER TABLE ALTER COLUMN ... TYPE statement
```

See [Aurora DSQL ALTER TABLE syntax support](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/alter-table-syntax-support.html)
for details on supported ALTER TABLE operations.

**Affected Django contrib migrations:**

- `auth.0002_alter_permission_name_max_length`
    - Table: `auth_permission`
    - Operation: AlterField on `name` column (max_length 50→255)
- `auth.0003_alter_user_email_max_length`
    - Table: `auth_user`
    - Operation: AlterField on `email` column (max_length 75→254)
- `auth.0008_alter_user_username_max_length`
    - Table: `auth_user`
    - Operations: AlterField on `username` column (max_length 30→150, updated validators and help text)
- `auth.0009_alter_user_last_name_max_length`
    - Table: `auth_user`
    - Operation: AlterField on `last_name` column (max_length 30→150)
- `auth.0010_alter_group_name_max_length`
    - Table: `auth_group`
    - Operation: AlterField on `name` column (max_length 80→150)
- `auth.0012_alter_user_first_name_max_length`
    - Table: `auth_user`
    - Operation: AlterField on `first_name` column (max_length 30→150)

**Workaround:**

Changing a column's physical type still requires a staged migration or table
recreation. Keep Django's model state synchronized with manual SQL by using
`SeparateDatabaseAndState` or `RunSQL(..., state_operations=[...])`.

For upstream contrib migrations that can't be changed, manually recreate the
affected table with its final schema:

1. Create a new table with the final schema as described in the migration file (migration files can be found in
   the [Django GitHub repository](https://github.com/django/django/tree/main/django/contrib))
2. Copy data from the existing table to the new table
3. Drop the old table and rename the new table
4. Verify the final schema and row counts
5. Mark only the matching migration as complete using the `--fake` flag:
   ```bash
   python manage.py migrate <app_name> <migration_number> --fake
   ```

See [Django migrations on Aurora DSQL](MIGRATIONS.md) for migration planning,
transaction, and data migration guidance.
