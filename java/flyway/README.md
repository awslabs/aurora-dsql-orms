# Aurora DSQL Flyway Support

Flyway database plugin for [Amazon Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/).

## Overview

This plugin enables [Flyway](https://flywaydb.org/) database migrations to work with Amazon Aurora DSQL by handling DSQL-specific behaviors:

- Recognizes `jdbc:aws-dsql:` JDBC URLs
- Bypasses `SET ROLE` commands (DSQL uses IAM authentication)
- Handles one-DDL-per-transaction requirement
- Bypasses advisory locks (DSQL uses optimistic concurrency control)
- Properly drops views before tables during `flyway clean`

## Quick Start

### 1. Add the Plugin JAR

Copy the JAR to your Flyway installation:

```bash
cp aurora-dsql-flyway-support-1.0.0.jar /flyway/drivers/
```

### 2. Add Required Dependencies

Ensure these JARs are also in `/flyway/drivers/`:

- `aurora-dsql-jdbc-connector-1.3.0.jar` (and its transitive dependencies)
- `postgresql-42.7.2.jar`

### 3. Configure Flyway

```properties
# flyway.conf
flyway.url=jdbc:aws-dsql:postgresql://<CLUSTER_ID>.dsql.<REGION>.on.aws:5432/postgres
flyway.user=admin
flyway.driver=software.amazon.dsql.jdbc.DSQLConnector
```

### 4. Run Migrations

```bash
flyway migrate
```

## Writing DSQL-Compatible Migrations

Aurora DSQL has specific constraints you must follow in your migration scripts.

### Supported Operations

```sql
-- Use UUID for primary keys
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL
);

-- Use CREATE INDEX ASYNC (required for DSQL)
CREATE INDEX ASYNC idx_users_email ON users(email);

-- Use DELETE for removing data
DELETE FROM users WHERE status = 'inactive';
```

### Unsupported Operations

```sql
-- SERIAL/BIGSERIAL not supported - use UUID instead
CREATE TABLE users (
    id SERIAL PRIMARY KEY
);

-- Synchronous indexes not supported - use ASYNC
CREATE INDEX idx_users_email ON users(email);

-- TRUNCATE not supported - use DELETE FROM
TRUNCATE TABLE users;

-- Foreign keys not supported
CREATE TABLE orders (
    user_id UUID REFERENCES users(id)
);

-- Array types not supported
CREATE TABLE tags (
    values TEXT[]
);
```

### Transaction Limits

- Maximum 3,000 rows per transaction
- Maximum 10 MiB data size per transaction
- Maximum 5 minutes per transaction

## Docker Setup

```dockerfile
ARG FLYWAY_VERSION=11.3

# Stage 1: Download dependencies
FROM maven:3.9-eclipse-temurin-17 AS deps
WORKDIR /build

RUN echo '<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion>\
<groupId>com.example</groupId><artifactId>deps</artifactId><version>1.0.0</version>\
<dependencies>\
<dependency><groupId>software.amazon.dsql</groupId><artifactId>aurora-dsql-jdbc-connector</artifactId><version>1.3.0</version></dependency>\
<dependency><groupId>software.amazon.dsql</groupId><artifactId>aurora-dsql-flyway-support</artifactId><version>1.0.0</version></dependency>\
<dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId><version>42.7.2</version></dependency>\
</dependencies></project>' > pom.xml

RUN mvn dependency:copy-dependencies -DoutputDirectory=/build/drivers

# Stage 2: Flyway image
FROM flyway/flyway:${FLYWAY_VERSION}

USER root
RUN rm -f /flyway/lib/postgresql-*.jar /flyway/drivers/postgresql-*.jar

COPY --from=deps /build/drivers/*.jar /flyway/drivers/

ENV FLYWAY_LOCATIONS=filesystem:sql
ENV FLYWAY_CONNECT_RETRIES=60
ENV FLYWAY_POSTGRESQL_TRANSACTIONAL_LOCK=false

COPY ./migrations/ /flyway/sql/

ENTRYPOINT ["flyway", "migrate"]
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
mvn clean package
```

Output: `target/aurora-dsql-flyway-support-1.0.0-SNAPSHOT.jar`

### Running Tests

Unit tests:
```bash
mvn test
```

Integration tests (requires DSQL cluster):
```bash
export DSQL_CLUSTER_ENDPOINT=<cluster-id>.dsql.<region>.on.aws
export AWS_REGION=<region>
mvn verify -P integration-test
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

- Verify IAM permissions include `dsql:DbConnectAdmin`
- Check AWS credentials are configured
- Tokens expire after 15 minutes; ensure fresh credentials

## Requirements

- Java 17+
- Flyway 11.3+
- Aurora DSQL JDBC Connector 1.3.0+
- PostgreSQL JDBC Driver 42.7.x

## Security

See [CONTRIBUTING](CONTRIBUTING.md) for more information.

## License

This project is licensed under the Apache-2.0 License.
