# Developer Instructions

## Building

```bash
cd java/hibernate/dialect
./gradlew build
```

## Running Tests

Unit tests:
```bash
./gradlew test
```

Integration tests (requires a live DSQL cluster):
```bash
RUN_INTEGRATION=TRUE ./gradlew test
```

Configuration tests (run in isolation):
```bash
./gradlew configurationTests
```

## Publishing

To publish to Maven Central staging:
```bash
./gradlew publish
```

To upload to Maven Central:
```bash
JRELEASER_MAVENCENTRAL_STAGE=UPLOAD ./gradlew jreleaserDeploy
```

## Project Structure

```
dialect/
├── build.gradle                    # Build configuration (Hibernate 7.2+ dependency)
├── settings.gradle                 # Project settings
├── src/
│   ├── main/java/software/amazon/dsql/hibernate/dialect/
│   │   ├── AuroraDSQLDialect.java          # Main dialect class
│   │   ├── AuroraDSQLIdentitySupport.java  # Identity column support
│   │   └── AuroraDSQLSequenceSupport.java  # Sequence support
│   └── test/java/software/amazon/dsql/hibernate/dialect/
│       ├── AuroraDSQLDialectTest.java           # Core dialect unit tests
│       ├── AuroraDSQLDialectFunctionsTest.java  # Function/formatting tests
│       └── integration/                         # Integration tests (require DSQL cluster)
```

## Hibernate Version Compatibility

This version (2.0.0) targets Hibernate ORM 7.2+ and is forward-compatible
through 7.4+. Key differences from the 1.0.x branch (Hibernate 6.6):

- `PgJdbcHelper` imported from `org.hibernate.dialect.type` (relocated in Hibernate 7.0)
- PostgreSQL JDBC types imported from `org.hibernate.dialect.type` package
- `PostgreSQLSqlAstTranslator` imported from `org.hibernate.dialect.sql.ast`
- `JavaTypeRegistry.resolveDescriptor()` used instead of `getDescriptor()`
- `PostgreSQLUUIDJdbcType` from `org.hibernate.dialect.type` replaces inline implementation
- Removed custom `LockingStrategy` implementation (Hibernate 7.x uses new locking SPI)
- Uses `int` overloads of `getWriteLockString` (deprecated but still functional; avoids
  importing `Timeout`/`Timeouts` which are new in 7.0 and may shift)
