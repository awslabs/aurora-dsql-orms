# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-09-18

### Changed

- `relationMode = "prisma"` is optional. Native foreign-key mode supports
  `NO ACTION`, `RESTRICT`, `CASCADE`, `SET NULL`, and `SET DEFAULT`.
  Prisma-generated `ALTER TABLE ... ADD FOREIGN KEY` migrations are preserved
  and marked `NOT VALID`; add a separate
  `ALTER TABLE ASYNC ... VALIDATE CONSTRAINT` statement to validate existing
  rows.
- Validate schemas through the same `dsql-lint --fix` path used for migration
  transformation. Fixable SQL passes with advisories; unfixable SQL still
  fails.
- Resolve `@aws/dsql-lint` through npm's `latest` dist-tag on fresh dependency
  resolution.

## [0.1.2] - 2026-05-13

### Changed

- Replace the custom SQL transform with dsql-lint and delegate validator
  checks to it.
- Consume `dsql-lint` via the new `@aws/dsql-lint` npm package: the
  prebuilt platform binary is resolved automatically, replacing the
  previous `cargo install dsql-lint` prerequisite. `DSQL_LINT_PATH`
  still takes precedence for custom or existing installations.
- Switch the transformer and validator to dsql-lint's `--format json`
  and stdin interface. Removes temp-file round-trips and regex-based
  stderr scraping in favor of typed diagnostics.
- CLI now honors dsql-lint's exit-code contract:
  - `0` clean, or all fixes applied without warnings
  - `1` unfixable errors remain
  - `2` usage error (propagated from dsql-lint)
  - `3` fixes applied with advisories —
    the migration is written; review warnings before applying
- Validate the dsql-lint JSON `schema_version` at parse time and fail
  with a clear version-skew message if it diverges.
- Replace inline DSQL limitation language with links to the official
  Aurora DSQL documentation.

### Fixed

- Reject unknown CLI flags instead of silently ignoring them.

## [0.1.0] - 2026-02-03

### Added

- Initial release of Aurora DSQL Prisma Tools
- Schema validator for DSQL compatibility checking
- Migration transformer for DSQL-required SQL transformations
- All-in-one migrate command for streamlined workflow
- Veterinary app example with DsqlPrismaClient
