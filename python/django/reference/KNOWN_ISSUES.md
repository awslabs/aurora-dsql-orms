# Known Issues

This document tracks known issues and workarounds when using the Aurora DSQL adapter for Django.

## Framework Issues

### Server-side cursors not supported

**Issue:** Django admin and large querysets fail with:

```
NotSupportedError: unsupported statement: DeclareCursor
```

**Root Cause:** Aurora DSQL does not support server-side cursors (`DECLARE CURSOR` statements).

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

### Django Sites Framework not supported

**Issue:** Django's sites framework fails with:

```
django.db.utils.ProgrammingError: operator does not exist: uuid = integer
LINE 1: ...le.com', "name" = 'example.com' WHERE "django_site"."id" = 1
```

**Root Cause:** The Aurora DSQL adapter for Django uses UUID for `AutoField`, but Django's sites framework hardcodes
`SITE_ID = 1` (integer) and expects integer primary keys.

**Workaround:** Remove `django.contrib.sites` from `INSTALLED_APPS` and avoid its use.

## Migration Issues

### ALTER COLUMN operations not supported

**Issue:** Default Django migrations that use `ALTER TABLE ALTER COLUMN` statements fail with:

```
psycopg.errors.FeatureNotSupported:
    unsupported ALTER TABLE ALTER COLUMN ... statement
```

**Root Cause:** Aurora DSQL does not support `ALTER COLUMN` operations.
See [Aurora DSQL ALTER TABLE syntax support](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-supported-sql-subsets.html#alter-table-syntax-support)
for details.

**Affected Migrations:**

- `contenttypes.0002_remove_content_type_name`
    - Table: `django_content_type`
    - Operations: AlterField on `name` column (set null=True), RemoveField on `name` column
- `auth.0002_alter_permission_name_max_length`
    - Table: `auth_permission`
    - Operation: AlterField on `name` column (max_length 50→255)
- `auth.0003_alter_user_email_max_length`
    - Table: `auth_user`
    - Operation: AlterField on `email` column (max_length 75→254)
- `auth.0005_alter_user_last_login_null`
    - Table: `auth_user`
    - Operations: AlterField on `last_login` column (added null=True, blank=True)
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

⚠️ **WARNING: Data loss may occur. Exercise extreme caution when performing these operations.**

Manually recreate affected tables with the correct schema:

1. Create a new table with the final schema as described in the migration file (migration files can be found in
   the [Django GitHub repository](https://github.com/django/django/tree/main/django/contrib))
2. Copy data from the existing table to the new table
3. Drop the old table and rename the new table
4. Mark the migration as complete using the `--fake` flag:
   ```bash
   python manage.py migrate <app_name> <migration_number> --fake
   ```
