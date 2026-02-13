# Aurora DSQL Dialect for Hibernate

[![GitHub](https://img.shields.io/badge/github-awslabs/aurora--dsql--orms-blue?logo=github)](https://github.com/awslabs/aurora-dsql-orms)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](https://github.com/awslabs/aurora-dsql-orms/blob/main/java/hibernate/LICENSE.Apache-2.0)
[![License](https://img.shields.io/badge/license-LGPL--2.1-brightgreen)](https://github.com/awslabs/aurora-dsql-orms/blob/main/java/hibernate/LICENSE.LGPL-2.1)
[![Maven Central Version](https://img.shields.io/maven-central/v/software.amazon.dsql/aurora-dsql-hibernate-dialect)](https://central.sonatype.com/artifact/software.amazon.dsql/aurora-dsql-hibernate-dialect)
[![Discord chat](https://img.shields.io/discord/1435027294837276802.svg?logo=discord)](https://discord.com/invite/nEF6ksFWru)

## Introduction

The Aurora DSQL dialect for Hibernate provides integration between Hibernate ORM and Aurora DSQL. This dialect enables
Java applications to leverage Hibernate's powerful object-relational mapping capabilities while taking advantage of
Aurora DSQL's distributed architecture and high availability.

## Sample Application

There is an included sample application in [examples/pet-clinic-app](examples/pet-clinic-app) that shows how to use Aurora DSQL
with Hibernate. To run the included example please refer to the [sample README](examples/pet-clinic-app/README.md).

## Prerequisites

- Java 17 or higher
- Hibernate version 6.6
- A connection to an Amazon Aurora DSQL database
- PostgreSQL JDBC driver version 42.x or higher

## Setup

A dialect for Aurora DSQL is used in largely the same way as other dialects for other databases. It is added
as a dependency to your Maven or Gradle application:

```
// Maven
<dependency>
    <groupId>software.amazon.dsql</groupId>
    <artifactId>aurora-dsql-hibernate-dialect</artifactId>
    <version>1.0.0</version>
    <type>pom</type>
</dependency>

// Gradle
implementation("software.amazon.dsql:aurora-dsql-hibernate-dialect:1.0.0")
```

With the `aurora-dsql-hibernate-dialect` JAR included in your Java application, the dialect can then be configured in a few ways:
- In a Hibernate.properties file: `hibernate.dialect=software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect`
- In persistence.xml: `<property name="hibernate.dialect" value="software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect"/>`
- In Spring application properties: `spring.jpa.properties.hibernate.dialect=software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect`
- Programmatically using `StandardServiceRegistryBuilder`, the configuration API, or in a `SessionFactory`

Hibernate will not automatically detect the DSQL dialect based on metadata, it must be explicitly specified or else
the PostgreSQLDialect will be used instead. With the dependency in place and the property set in Hibernate,
the AuroraDSQLDialect will then automatically be used in DB interactions. Depending on your logging configuration, this
may be verified in logs as connections are created.

See [Hibernate documentation](https://docs.jboss.org/hibernate/orm/6.6/introduction/html_single/Hibernate_Introduction.html#configuration)
for more information on configuring your Hibernate application, including setting the dialect.

### Database Connection

Configure your database connection for DSQL as follows:

```properties
hibernate.connection.url=jdbc:postgresql://<cluster_endpoint>/postgres?sslMode=verify-full&sslNegotiation=direct
hibernate.connection.username=<username>
hibernate.connection.driver_class=org.postgresql.Driver
```

## Best practices

### Primary key generation

Server-generated UUIDs are the recommended choice for primary key columns. They can be added to your entity definitions as follows:

```java
@Id
@GeneratedValue
@Column(name = "id", updatable = false, nullable = false, columnDefinition = "UUID DEFAULT gen_random_uuid()")
private UUID id;
```

Sequence and identity based keys are also supported in DSQL, and can be used for integer primary keys. The Hibernate
dialect uses a default `CACHE` parameter of 65536 in sequence and identity definitions, but this can be overridden
using the configuration property `hibernate.dialect.aurora_dsql.sequence_cache_size`, configurable in the same ways
as the dialect choice above. See the [Working with sequences and identity columns](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/sequences-identity-columns-working-with.html) page
for guidance on choosing the appropriate cache size for your workload.

### Auto-DDL

Usage of an automatically generated schema with Hibernate is not recommended with DSQL. While it may be useful
for experimental development or testing environments, it should not be used in production. An automatically generated
schema can perform poorly, and can be destructive in unexpected ways.

### Concurrency control and locking

[Aurora DSQL uses optimistic concurrency control (OCC)](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-concurrency-control.html), where conflicts are presumed to be rare. Conflicts are only handled
when they occur, by allowing the first transaction to commit successfully, while any later transaction commit will result
in an error. This has largely the same effect as Hibernate's built in version-based `OPTIMISTIC` lock mode. Users should
therefore not use Hibernate's `OPTIMISTIC` lock mode, as DSQL will always trigger an OCC error prior to committing if
there is a conflict, rendering the version check unnecessary.

**There are only two lock modes that should be used: `NONE` (which will still use standard DSQL OCC), and `PESSIMISTIC_WRITE`.** Although DSQL will always use
optimistic locking, in Hibernate `PESSIMISTIC_WRITE` will add the `SELECT ... FOR UPDATE` modifier, which adds additional
read checks on selected rows, preventing commits if rows read are modified by another transaction. There are multiple
examples of how DSQL's concurrency control works [available here in an AWS blog](https://aws.amazon.com/blogs/database/concurrency-control-in-amazon-aurora-dsql/),
including with `SELECT ... FOR UPDATE`. DSQL does not support any other locking modes, and so only these two Hibernate
locking modes should be used.

## Dialect Features and Limitations

Dialects provide syntax and supported features to allow the Hibernate ORM to correctly handle differences between databases.
As Aurora DSQL is PostgreSQL-compatible and supports most PostgreSQL features, much of the dialect is similar to that of PostgreSQL.
There are some key differences however that will help ensure a seamless developer experience with Hibernate
and Aurora DSQL. The list below contains some of the key differences from the PostgreSQL dialect:

- **Data types**: The dialect provides correct `float`, `double` and `numeric` precision as well as `varchar` size limits.
- **Foreign Keys**: Aurora DSQL does not support foreign key constraints. The dialect disables these constraints, but be aware that referential integrity must be maintained at the application level.
- **Index creation**: Aurora DSQL does not support `CREATE INDEX` or `CREATE UNIQUE INDEX` commands. The dialect instead uses `CREATE INDEX ASYNC` and `CREATE UNIQUE INDEX ASYNC` commands. See the [Asynchronous indexes in Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-create-index-async.html) page for more information.
- **Locking**: Aurora DSQL uses optimistic concurrency control (OCC) with support for `SELECT ... FOR UPDATE`. The dialect supports these two locking methods. See the [Concurrency control in Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-concurrency-control.html) page for more information.
- **Sequences**: The dialect implements correct syntax for Aurora DSQL sequence and identity support, including the mandatory `CACHE` parameter. See the [Sequences and identity columns](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/sequences-identity-columns.html) page for more information.
- **Temporary tables**: Aurora DSQL does not support temporary tables. The dialect will use standard tables instead. These tables will appear with `HT_` or `HTE_` prefixes, and will be managed automatically by Hibernate.
- **Truncate command**: Aurora DSQL does not support `TRUNCATE` command. The dialect uses a `DELETE` command instead.


## Developer instructions

Instructions on how to build and test the dialect are available in the [Developer Instructions](dialect/README.md).

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
