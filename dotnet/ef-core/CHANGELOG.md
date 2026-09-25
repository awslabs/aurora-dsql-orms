# Changelog

## [1.1.0] - 2026-09-25

### Added
- Native foreign-key support. Aurora DSQL enforces foreign keys and supports
  `NoAction`, `Restrict`, `Cascade`, `SetNull`, and `SetDefault`. Constraints
  added to an existing table use `NOT VALID` followed by
  `ALTER TABLE ASYNC ... VALIDATE CONSTRAINT`; the migration transformer reports
  when it cannot apply the complete sequence.

### Changed
- Pinned `Amazon.AuroraDsql.Lint.Runtime` to `0.2.15`, which preserves
  foreign-key DDL instead of removing it.
- Documented that cascading actions count toward transaction row limits and that
  foreign-key conflicts can surface as serialization failures handled by
  `DsqlExecutionStrategy`.

## [1.0.0] - 2026-06-26

### Added
- Initial release targeting Entity Framework Core 9.x on .NET 8.
- Connection wrapping over Npgsql with IAM authentication via `DsqlDataSource`.
- Automatic OCC retry (SqlState 40001/OC000/OC001) via `DsqlExecutionStrategy`.
- UUID and IDENTITY primary key conventions.
- Migration support via `DsqlMigrator` with dsql-lint DDL transformation
  (`CREATE INDEX ASYNC`, `IF NOT EXISTS` idempotency).
- InventoryApi sample app demonstrating CRUD, OCC retry, batch operations,
  navigation properties, and migrations.
