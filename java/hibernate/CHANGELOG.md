# Changelog

## [2.0.0] - 2026-06-14

### Breaking Changes
- **Minimum Hibernate version raised to 7.2+** (Spring Boot 4.x). Users on Hibernate 6.6.x / Spring Boot 3.x should remain on version 1.0.x.

### Fixed
- `NoClassDefFoundError: org/hibernate/dialect/PgJdbcHelper` when used with Hibernate 7.x (#issue). The class was relocated to `org.hibernate.dialect.type.PgJdbcHelper` in Hibernate 7.0.
- Updated all PostgreSQL JDBC type imports to use `org.hibernate.dialect.type` package (relocated in Hibernate 7.0).
- Updated `PostgreSQLSqlAstTranslator` import to `org.hibernate.dialect.sql.ast` (relocated in Hibernate 7.0).
- Updated `JavaTypeRegistry` call from `getDescriptor()` to `resolveDescriptor()` (API change in Hibernate 7.0).
- Replaced inline `PostgreSQLUUIDJdbcType` implementation with the standard `org.hibernate.dialect.type.PostgreSQLUUIDJdbcType` (available since Hibernate 7.0).
- Removed custom `LockingStrategy` overrides that referenced the removed `Lockable` type.

### Changed
- Compile dependency updated from `org.hibernate:hibernate-core:6.6.x` to `org.hibernate.orm:hibernate-core:7.2.12.Final`.
- Maven artifact coordinates unchanged: `software.amazon.dsql:aurora-dsql-hibernate-dialect:2.0.0`.

## [1.0.1] - 2025-02-xx

### Added
- Sequence and identity column support with configurable `CACHE` parameter.

## [1.0.0] - 2025-01-xx

### Added
- Initial release targeting Hibernate 6.6.x.
- Aurora DSQL-specific dialect features: async indexes, no foreign keys, OCC locking, DELETE-as-truncate.
