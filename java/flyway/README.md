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

Example Dockerfile for running Flyway migrations against Aurora DSQL:

```dockerfile
FROM flyway/flyway:11.3

USER root

# Remove bundled PostgreSQL driver (we'll use the one from DSQL connector)
RUN rm -f /flyway/lib/postgresql-*.jar /flyway/drivers/postgresql-*.jar

# Copy required JARs (download these from Maven Central)
COPY ./drivers/*.jar /flyway/drivers/

# Copy your migration scripts
COPY ./migrations/ /flyway/sql/

ENV FLYWAY_LOCATIONS=filesystem:sql
ENV FLYWAY_CONNECT_RETRIES=60

ENTRYPOINT ["flyway", "migrate"]
```

Required JARs in `./drivers/`:
- `aurora-dsql-flyway-support-1.0.0.jar`
- `aurora-dsql-jdbc-connector-1.3.0.jar` (and its transitive dependencies)
- `postgresql-42.7.2.jar`

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

### "change conflicts with another transaction, please retry" (OC000)

This is an optimistic concurrency control (OCC) conflict. Aurora DSQL uses OCC instead of locks, and conflicts are detected at commit time. This error is rare during migrations since they typically run single-threaded.

If you encounter this error, simply re-run `flyway migrate`. Flyway migrations are idempotent - already-applied migrations will be skipped.

For more information, see [Concurrency control in Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-concurrency-control.html).

## Requirements

- Java 17+
- Flyway 11.3+
- Aurora DSQL JDBC Connector 1.3.0+
- PostgreSQL JDBC Driver 42.7.x

## Security

See [CONTRIBUTING](CONTRIBUTING.md) for more information.

## License

This project is licensed under the Apache-2.0 License.
