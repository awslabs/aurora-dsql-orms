# Amazon Aurora DSQL dialect for SQLAlchemy

[![GitHub](https://img.shields.io/badge/github-awslabs/aurora--dsql--orms-blue?logo=github)](https://github.com/awslabs/aurora-dsql-orms)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](https://github.com/awslabs/aurora-dsql-orms/blob/main/LICENSE)
[![PyPI - Version](https://img.shields.io/pypi/v/aurora-dsql-sqlalchemy)](https://pypi.org/project/aurora-dsql-sqlalchemy)
[![Discord chat](https://img.shields.io/discord/1435027294837276802.svg?logo=discord)](https://discord.com/invite/nEF6ksFWru)

## Introduction

The Aurora DSQL dialect for SQLAlchemy provides integration between SQLAlchemy ORM and Aurora DSQL. This dialect enables
Python applications to leverage SQLAlchemy's powerful object-relational mapping capabilities while taking advantage of
Aurora DSQL's distributed architecture and high availability.

## Sample Application

There is an included sample application in [examples/pet-clinic-app](examples/pet-clinic-app) that shows how to use Aurora DSQL
with SQLAlchemy. To run the included example please refer to the [sample README](examples/pet-clinic-app#readme).

## Prerequisites

- Python 3.10 or higher
- SQLAlchemy 2.0.0 or higher
- One of the following drivers:
  - psycopg 3.2.0 or higher
  - psycopg2 2.9.0 or higher

## Installation

Install the packages using the commands below:

```bash
pip install aurora-dsql-sqlalchemy

# driver installation (in case you opt for psycopg)
# DO NOT use pip install psycopg-binary
pip install "psycopg[binary]"

# driver installation (in case you opt for psycopg2)
pip install psycopg2-binary
```

## Dialect Configuration

After installation, you can connect to an Aurora DSQL cluster using the `create_dsql_engine` helper function:

```python
from aurora_dsql_sqlalchemy import create_dsql_engine

engine = create_dsql_engine(
    host="<CLUSTER_ENDPOINT>",
    user="<CLUSTER_USER>",
    driver="psycopg",  # or "psycopg2"
)
```

The helper function handles:
- IAM authentication via the Aurora DSQL Python Connector
- SSL configuration with certificate verification
- Direct SSL negotiation optimization (when supported by libpq >= 17)
- Connection pooling with sensible defaults

For more control, you can customize additional parameters:

```python
engine = create_dsql_engine(
    host="<CLUSTER_ENDPOINT>",
    user="<CLUSTER_USER>",
    driver="psycopg",
    pool_size=10,
    max_overflow=20,
)
```

**Note:** Each connection has a maximum duration limit. See the `Maximum connection duration` time limit in the [Cluster quotas and database limits in Amazon Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/CHAP_quotas.html) page.

### SSL/TLS Configuration

Aurora DSQL requires TLS for all connections. Plaintext connections are not supported. Enabling certificate verification protects against on-path and impersonation attacks.

`create_dsql_engine` defaults to:
- `sslmode="verify-full"` - verifies the server certificate and hostname
- `sslrootcert="system"` - uses the default certificate authority (CA) trust defined by libpq’s TLS backend

See [SSL Configuration](docs/SSL_CONFIGURATION.md) for detailed setup instructions.

## Best Practices

### Primary Key Generation

SQLAlchemy applications connecting to Aurora DSQL should use UUID for the primary key column since auto-incrementing integer keys (sequences or serial) are not supported in DSQL. The following column definition can be used to define an UUID primary key column.

```python
Column(
    "id",
    UUID(as_uuid=True),
    primary_key=True,
    default=text('gen_random_uuid()')
)
```

`gen_random_uuid()` returns an UUID version 4 as the default value.

## Dialect Features and Limitations

- **Column Metadata**: The dialect fixes an issue related to `"datatype json not supported"` when calling SQLAlchemy's metadata() API.
- **Foreign Keys**: Aurora DSQL does not support foreign key constraints. The dialect disables these constraints, but be aware that referential integrity must be maintained at the application level.
- **Index Creation**: Aurora DSQL does not support `CREATE INDEX` or `CREATE UNIQUE INDEX` commands. The dialect instead uses `CREATE INDEX ASYNC` and `CREATE UNIQUE INDEX ASYNC` commands. See the [Asynchronous indexes in Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-create-index-async.html) page for more information.

  The following parameters are used for customizing index creation

  - `auroradsql_include` - specifies which columns to includes in an index by using the `INCLUDE` clause:

    ```python
    Index(
        "include_index",
        table.c.id,
        auroradsql_include=['name', 'email']
    )
    ```

    Generated SQL output:

    ```sql
    CREATE INDEX ASYNC include_index ON table (id) INCLUDE (name, email)
    ```

  - `auroradsql_nulls_not_distinct` - controls how `NULL` values are treated in unique indexes:

    ```python
    Index(
        "idx_name",
        table.c.column,
        unique=True,
        auroradsql_nulls_not_distinct=True
    )
    ```

    Generated SQL output:

    ```sql
    CREATE UNIQUE INDEX idx_name ON table (column) NULLS NOT DISTINCT
    ```

- **Index Interface Limitation**: `NULLS FIRST | LAST` - SQLalchemy's Index() interface does not have a way to pass in the sort order of null and non-null columns. (Default: `NULLS LAST`). If `NULLS FIRST` is required, please refer to the syntax as specified in [Asynchronous indexes in Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-create-index-async.html) and execute the corresponding SQL query directly in SQLAlchemy.
- **Psycopg (psycopg3) support**: When connecting to DSQL using the default postgresql dialect with psycopg, an unsupported `SAVEPOINT` error occurs. The DSQL dialect addresses this issue by disabling the `SAVEPOINT` during connection.

## Developer instructions

Instructions on how to build and test the dialect are available in the [Developer Instructions](aurora_dsql_sqlalchemy/README.md).

## Security

See [CONTRIBUTING](../../CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
