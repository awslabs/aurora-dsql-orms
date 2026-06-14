# Aurora DSQL Dialect for Hibernate

[![GitHub](https://img.shields.io/github/license/awslabs/aurora-dsql-orms)](LICENSE.Apache-2.0)
[![Maven Central Version](https://img.shields.io/maven-central/v/software.amazon.dsql/aurora-dsql-hibernate-dialect)](https://central.sonatype.com/artifact/software.amazon.dsql/aurora-dsql-hibernate-dialect)

## Introduction

The Aurora DSQL dialect for Hibernate provides integration between Hibernate ORM
and Aurora DSQL. This dialect enables Java applications to leverage Hibernate's
powerful object-relational mapping capabilities while taking advantage of
Aurora DSQL's distributed architecture and high availability.

## Version Compatibility

| Dialect Version | Hibernate ORM | Spring Boot | Java |
|----------------|---------------|-------------|------|
| 1.0.x          | 6.6.x         | 3.x         | 17+  |
| **2.0.0**      | **7.2+**      | **4.x**     | 17+  |

> **Note:** Version 2.0.0 targets Hibernate ORM 7.2+ and is incompatible with
> Hibernate 6.x. If you are on Spring Boot 3.x, continue using version 1.0.x.

## Prerequisites

- Java 17 or higher
- Hibernate ORM 7.2+
- A connection to an Amazon Aurora DSQL database
- PostgreSQL JDBC driver version 42.x or higher

## Setup

Add the dependency to your Maven or Gradle application:

```xml
<!-- Maven -->
<dependency>
    <groupId>software.amazon.dsql</groupId>
    <artifactId>aurora-dsql-hibernate-dialect</artifactId>
    <version>2.0.0</version>
</dependency>
```

```groovy
// Gradle
implementation("software.amazon.dsql:aurora-dsql-hibernate-dialect:2.0.0")
```

Configure the dialect in your application:

- In Spring application properties:
  `spring.jpa.properties.hibernate.dialect=software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect`
- In persistence.xml:
  `<property name="hibernate.dialect" value="software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect"/>`
- In Hibernate.properties:
  `hibernate.dialect=software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect`

Hibernate will not automatically detect the DSQL dialect based on metadata — it
must be explicitly specified or else the PostgreSQLDialect will be used instead.

### Database Connection

```properties
hibernate.connection.url=jdbc:postgresql://<cluster_endpoint>/postgres?sslMode=verify-full&sslNegotiation=direct
hibernate.connection.username=<username>
hibernate.connection.driver_class=org.postgresql.Driver
```

## Best practices

### Primary key generation

Server-generated UUIDs are the recommended choice for primary key columns:

```java
@Id
@GeneratedValue
@Column(name = "id", updatable = false, nullable = false, columnDefinition = "UUID DEFAULT gen_random_uuid()")
private UUID id;
```

Sequence and identity based keys are also supported. The dialect uses a default
`CACHE` parameter of 65536, configurable via
`hibernate.dialect.aurora_dsql.sequence_cache_size`.

### Auto-DDL

Usage of automatically generated schema with Hibernate is not recommended with
DSQL in production. It may be useful for experimental development or testing.

### Concurrency control and locking

Aurora DSQL uses optimistic concurrency control (OCC) exclusively. Conflicts are
handled at commit time by allowing the first transaction to succeed while later
conflicting transactions receive an error.

Users should not use Hibernate's `OPTIMISTIC` lock mode, as DSQL handles OCC
natively. The only two lock modes that should be used are:

- `NONE` — standard DSQL OCC
- `PESSIMISTIC_WRITE` — adds `SELECT ... FOR UPDATE`, which provides additional
  read checks on selected rows

## Dialect Features

- **Data types:** Correct `float`, `double`, `numeric` precision and `varchar` size limits.
- **Foreign Keys:** Disabled — referential integrity is maintained at the application level.
- **Index creation:** Uses `CREATE INDEX ASYNC` and `CREATE UNIQUE INDEX ASYNC`.
- **Locking:** OCC with `SELECT ... FOR UPDATE` support.
- **Sequences:** Correct syntax with mandatory `CACHE` parameter.
- **Temporary tables:** Standard tables with `HT_`/`HTE_` prefixes are used instead.
- **Truncate:** Uses `DELETE` in place of `TRUNCATE`.

## Migration from 1.0.x

If upgrading from dialect version 1.0.x (Hibernate 6.6) to 2.0.0 (Hibernate 7.2+):

1. Upgrade to Spring Boot 4.x / Hibernate 7.2+
2. Replace the dependency version from `1.0.x` to `2.0.0`
3. No application code changes are needed — the dialect class name and
   configuration properties are unchanged.

## Developer instructions

Instructions on how to build and test the dialect are available in the
[Developer Instructions](dialect/README.md).

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
