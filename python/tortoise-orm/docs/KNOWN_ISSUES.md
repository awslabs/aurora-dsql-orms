# Known Issues

This document tracks known issues when using the Aurora DSQL adapter for Tortoise ORM. For Aurora DSQL SQL compatibility details, see the [Aurora DSQL documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html).

## Nested transactions

**Issue:** Nested `in_transaction()` or `atomic()` blocks fail.

**Why:** Tortoise ORM uses savepoints to implement nested transaction semantics.

**Workaround:** Restructure code to avoid nested transactions.

## SELECT FOR UPDATE

**Issue:** Calling `select_for_update()` on a queryset fails.

```python
# This will fail
await MyModel.filter(id=some_id).select_for_update().first()
```

**Workaround:** Aurora DSQL uses optimistic concurrency control (OCC). Remove `select_for_update()` calls and handle potential `SerializationFailure` errors with retry logic.

## update_or_create

**Issue:** Calling `update_or_create()` fails.

**Why:** The Tortoise ORM `update_or_create()` implementation uses `SELECT FOR UPDATE` internally.

**Workaround:** Use `bulk_create` with `on_conflict` for atomic upserts:

```python
class Item(Model):
    name = fields.CharField(max_length=100, unique=True)  # unique constraint required
    value = fields.CharField(max_length=100)

# Atomic upsert using ON CONFLICT
await Item.bulk_create(
    [Item(name="test", value="new_value")],
    on_conflict=["name"],
    update_fields=["value"],
)
```

Note: `bulk_create` does not return `(instance, created)`. Fetch the row afterward if needed.

## Foreign key constraints not enforced

**Issue:** Foreign key relationships defined in models are not enforced at the database level.

```python
class Pet(Model):
    owner = fields.ForeignKeyField("models.Owner", related_name="pets")
```

The relationship works for ORM queries and joins, but:
- Deleting an Owner does not cascade to Pets at the database level
- Inserting a Pet with a non-existent `owner_id` succeeds at the database level

**Workaround:** Implement referential integrity checks in application logic.

## Aerich compatibility module prevents side-by-side PostgreSQL use

**Issue:** Enabling the Aerich compatibility module (`aurora_dsql_tortoise.aerich_compat`) prevents using standard PostgreSQL and Aurora DSQL in the same application.

**Why:** The compatibility module patches global Aerich behavior to use DSQL-compatible DDL generation. These patches affect all database connections, not just DSQL connections.

**Workaround:** If you need to use both PostgreSQL and Aurora DSQL in the same application, do not include `aurora_dsql_tortoise.aerich_compat` in your models list. You will need to manage DSQL migrations manually.
