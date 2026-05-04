# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Consume `dsql-lint` via the new `@aws/dsql-lint` npm package: the
  prebuilt platform binary is resolved automatically, replacing the
  previous `cargo install dsql-lint` prerequisite. `DSQL_LINT_PATH`
  still takes precedence for custom or existing installations.
- Switch the transformer and validator to dsql-lint's `--format json`
  - stdin interface. Removes temp-file round-trips and regex-based
    stderr scraping in favor of typed diagnostics.
- CLI now honors dsql-lint's exit-code contract:
  - `0` clean, or all fixes applied without warnings
  - `1` unfixable errors remain
  - `2` usage error (propagated from dsql-lint)
  - `3` fixes applied with advisories (e.g. foreign keys removed) —
    the migration is written; review warnings before applying
- Validate the dsql-lint JSON `schema_version` at parse time and fail
  with a clear version-skew message if it diverges.

### Added

- Initial release of Aurora DSQL Prisma Tools
- Schema validator for DSQL compatibility checking
- Migration transformer for DSQL-required SQL transformations
- All-in-one migrate command for streamlined workflow
- Veterinary app example with DsqlPrismaClient
