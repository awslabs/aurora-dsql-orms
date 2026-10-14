# Changelog

All notable changes to the Aurora DSQL Flyway support plugin are documented in
this file.

## [1.0.0] - 2026-01-27

### Added

- Initial Aurora DSQL database plugin for Flyway 11.
- Recognition of `jdbc:aws-dsql:` JDBC URLs with IAM authentication through
  the Aurora DSQL JDBC connector.
- Aurora DSQL-compatible migration behavior, including one DDL statement per
  transaction, skipped advisory locks and `SET ROLE` commands, and safe view
  ordering during `flyway clean`.
- Gradle build, unit and integration tests, and Maven Central release
  automation.

[1.0.0]: https://github.com/awslabs/aurora-dsql-orms/releases/tag/java/flyway/v1.0.0
