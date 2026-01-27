# Aurora DSQL Flyway Support

Flyway database plugin for [Amazon Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/).

## Overview

This plugin enables [Flyway](https://flywaydb.org/) database migrations to work with Amazon Aurora DSQL by handling DSQL-specific behaviors:

- Recognizes `jdbc:aws-dsql:` JDBC URLs
- Bypasses `SET ROLE` commands (DSQL uses IAM authentication)
- Bypasses advisory locks (DSQL uses optimistic concurrency control)
- Properly drops views before tables during `flyway clean`

## Installation

The plugin is available on [Maven Central](https://central.sonatype.com/artifact/software.amazon.dsql/aurora-dsql-flyway-support).

### Maven

```xml
<dependency>
    <groupId>software.amazon.dsql</groupId>
    <artifactId>aurora-dsql-flyway-support</artifactId>
    <version>1.0.0</version>
</dependency>
```

### Gradle

```groovy
implementation 'software.amazon.dsql:aurora-dsql-flyway-support:1.0.0'
```

You'll also need these dependencies:

```xml
<!-- Aurora DSQL JDBC Connector -->
<dependency>
    <groupId>software.amazon.dsql</groupId>
    <artifactId>aurora-dsql-jdbc-connector</artifactId>
    <version>1.3.0</version>
</dependency>

<!-- Flyway -->
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-core</artifactId>
    <version>11.3.0</version>
</dependency>
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-database-postgresql</artifactId>
    <version>11.3.0</version>
</dependency>

<!-- PostgreSQL JDBC Driver -->
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <version>42.7.2</version>
</dependency>
```

## Quick Start

### 1. Configure Flyway

```properties
# flyway.conf
flyway.url=jdbc:aws-dsql:postgresql://<CLUSTER_ID>.dsql.<REGION>.on.aws:5432/postgres
flyway.user=admin
flyway.driver=software.amazon.dsql.jdbc.DSQLConnector
```

### 2. Run Migrations

```bash
flyway migrate
```

## Programmatic Usage

For Java applications, you can configure Flyway programmatically:

```java
Flyway flyway = Flyway.configure()
    .dataSource(
        "jdbc:aws-dsql:postgresql://<CLUSTER_ID>.dsql.<REGION>.on.aws:5432/postgres",
        "admin",
        null)  // Password is null - IAM auth is automatic
    .locations("classpath:db/migration")
    .load();

flyway.migrate();
```

For production applications with connection pooling, use HikariCP:

```java
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

HikariConfig config = new HikariConfig();
config.setJdbcUrl("jdbc:aws-dsql:postgresql://<CLUSTER_ID>.dsql.<REGION>.on.aws:5432/postgres");
config.setUsername("admin");
config.setMaximumPoolSize(10);
config.setConnectionTimeout(30000);

HikariDataSource dataSource = new HikariDataSource(config);

Flyway flyway = Flyway.configure()
    .dataSource(dataSource)
    .locations("classpath:db/migration")
    .load();

flyway.migrate();
```

The Aurora DSQL JDBC Connector automatically handles:
- IAM authentication token generation and refresh
- SSL/TLS configuration with certificate verification
- Connection URL transformation

## Writing DSQL-Compatible Migrations

When writing Flyway migrations for Aurora DSQL, follow these patterns:

### Primary Keys

Use UUID with `gen_random_uuid()` for primary keys:

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255)
);
```

### Index Creation

Use `CREATE INDEX ASYNC` for all indexes:

```sql
CREATE INDEX ASYNC idx_users_email ON users(email);
```

See [Asynchronous indexes in Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-create-index-async.html) for details.

### Data Modification

Use standard INSERT, UPDATE, and DELETE statements:

```sql
INSERT INTO users (email, name) VALUES ('user@example.com', 'Test User');
UPDATE users SET name = 'Updated Name' WHERE email = 'user@example.com';
DELETE FROM users WHERE email = 'user@example.com';
```

### Transaction Limits

Be aware of these per-transaction limits when writing migrations:

- Maximum 3,000 rows
- Maximum 10 MiB data size
- Maximum 5 minutes duration

For a complete list of PostgreSQL features not available in Aurora DSQL, see [Unsupported PostgreSQL features](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-unsupported-features.html) in the Aurora DSQL documentation.

## Docker Setup

Use a multi-stage Docker build to download all dependencies automatically:

```dockerfile
# Stage 1: Download dependencies using Maven
FROM maven:3.9-eclipse-temurin-21 AS deps

WORKDIR /deps

# Create a minimal pom.xml to download dependencies
RUN echo '<?xml version="1.0" encoding="UTF-8"?>\n\
<project xmlns="http://maven.apache.org/POM/4.0.0"\n\
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n\
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">\n\
    <modelVersion>4.0.0</modelVersion>\n\
    <groupId>deps</groupId>\n\
    <artifactId>flyway-dsql-deps</artifactId>\n\
    <version>1.0.0</version>\n\
    <dependencies>\n\
        <dependency>\n\
            <groupId>software.amazon.dsql</groupId>\n\
            <artifactId>aurora-dsql-flyway-support</artifactId>\n\
            <version>1.0.0</version>\n\
        </dependency>\n\
        <dependency>\n\
            <groupId>software.amazon.dsql</groupId>\n\
            <artifactId>aurora-dsql-jdbc-connector</artifactId>\n\
            <version>1.3.0</version>\n\
        </dependency>\n\
        <dependency>\n\
            <groupId>org.postgresql</groupId>\n\
            <artifactId>postgresql</artifactId>\n\
            <version>42.7.2</version>\n\
        </dependency>\n\
    </dependencies>\n\
</project>' > pom.xml

# Download all dependencies (including transitive)
RUN mvn dependency:copy-dependencies -DoutputDirectory=/deps/drivers -DincludeScope=runtime

# Stage 2: Flyway with DSQL support
FROM flyway/flyway:11.3

USER root

# Remove bundled PostgreSQL driver (we use the one from DSQL connector)
RUN rm -f /flyway/lib/postgresql-*.jar /flyway/drivers/postgresql-*.jar

# Copy downloaded dependencies
COPY --from=deps /deps/drivers/*.jar /flyway/drivers/

# Copy your migration scripts
COPY ./migrations/ /flyway/sql/

ENV FLYWAY_LOCATIONS=filesystem:sql
ENV FLYWAY_CONNECT_RETRIES=60

ENTRYPOINT ["flyway", "migrate"]
```

Build and run:

```bash
# Build the image
docker build -t flyway-dsql .

# Run migrations
docker run --rm \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN \
  -e FLYWAY_URL="jdbc:aws-dsql:postgresql://<CLUSTER_ID>.dsql.<REGION>.on.aws:5432/postgres" \
  -e FLYWAY_USER=admin \
  -e FLYWAY_DRIVER=software.amazon.dsql.jdbc.DSQLConnector \
  flyway-dsql
```

## IAM Configuration

The IAM role needs `dsql:DbConnectAdmin` permission:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "dsql:DbConnectAdmin",
            "Resource": "arn:aws:dsql:<REGION>:<ACCOUNT>:cluster/<CLUSTER_ID>"
        }
    ]
}
```

For EKS/IRSA, ensure these environment variables are set:
- `AWS_REGION`
- `AWS_ROLE_ARN`
- `AWS_WEB_IDENTITY_TOKEN_FILE`

## Building from Source

```bash
./gradlew build
```

Output: `build/libs/aurora-dsql-flyway-support-1.0.0.jar`

### Running Tests

Unit tests:
```bash
./gradlew test
```

Integration tests (requires DSQL cluster):
```bash
export DSQL_CLUSTER_ENDPOINT=<cluster-id>.dsql.<region>.on.aws
export AWS_REGION=<region>
./gradlew integrationTest
```

## Troubleshooting

### "No database found to handle jdbc:aws-dsql:"

The plugin JAR is not on the classpath. Ensure it is in `/flyway/drivers/`.

### "setting configuration parameter 'role' not supported"

You are using standard PostgreSQL support instead of this plugin. Verify:
1. Plugin JAR is present in `/flyway/drivers/`
2. URL starts with `jdbc:aws-dsql:`

### "Please use CREATE INDEX ASYNC"

DSQL requires async index creation. Change your migration:

```sql
-- Before
CREATE INDEX idx_name ON table(column);

-- After
CREATE INDEX ASYNC idx_name ON table(column);
```

### "ddl and dml are not supported in the same transaction"

This error occurs when using `flyway baseline` command. Aurora DSQL does not allow DDL (CREATE TABLE) and DML (INSERT) in the same transaction.

Use `baselineOnMigrate` instead of calling `baseline` directly:

```properties
# flyway.conf
flyway.baselineOnMigrate=true
flyway.baselineVersion=1
```

Or in Java:
```java
Flyway flyway = Flyway.configure()
    .dataSource(url, user, password)
    .baselineOnMigrate(true)
    .baselineVersion("1")
    .load();
flyway.migrate();
```

### Token/Authentication Errors

The Aurora DSQL JDBC Connector automatically handles IAM token generation and refresh. If you encounter authentication errors:

- Verify IAM permissions include `dsql:DbConnectAdmin`
- Check AWS credentials are configured (environment variables, IAM role, or credentials file)
- Ensure the AWS region is correctly set

## Requirements

- Java 21+
- Flyway 11.3+
- Aurora DSQL JDBC Connector 1.3.0+
- PostgreSQL JDBC Driver 42.7.x

## Security

See [CONTRIBUTING](CONTRIBUTING.md) for more information.

## License

This project is licensed under the Apache-2.0 License.
