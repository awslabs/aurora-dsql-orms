# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial release of the Aurora DSQL adapter for Drizzle ORM.
- `drizzle()` factory building an IAM-authenticated `AuroraDSQLPool` over
  `drizzle-orm/node-postgres`.
- `db.transactionWithRetry()` — opt-in, idempotent transactions with OCC retry
  (`OC000` / `OC001` / `40001`). Retry is owned at the adapter layer and
  classifies conflicts by recursively unwrapping Drizzle's wrapped `cause`; the
  callback receives a real transaction, and a nested transaction is rejected
  rather than silently committing the outer one. Throws
  `AwsDsqlRetryExhaustedError` on exhaustion.
- `migrate()` applying migrations statement-by-statement (autocommit) with a
  tracking table, resumable after partial failure; the stock node-postgres
  migrator instead sends every statement in one transaction. Waits for
  `CREATE INDEX ASYNC` builds to complete before recording, and rejects a
  breakpoint-free file that holds multiple statements.
- `aurora-dsql-drizzle` CLI: `generate` / `transform` / `lint`, rewriting migrations
  for DSQL via `dsql-lint` (>= 0.2) while preserving `--> statement-breakpoint`
  markers.
- Veterinary app example demonstrating the full workflow on a live cluster.

### Changed

- Preserve native foreign keys in generated migrations. Foreign keys created
  with `ALTER TABLE` are marked `NOT VALID`; add a separate `ALTER TABLE ASYNC
... VALIDATE CONSTRAINT` statement to validate existing rows.
- Require `@aws/dsql-lint` 0.2.17 or later for native foreign-key support.
