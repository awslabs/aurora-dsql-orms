# Aurora DSQL Adapter for Tortoise ORM

[![GitHub](https://img.shields.io/badge/github-awslabs/aurora--dsql--orms-blue?logo=github)](https://github.com/awslabs/aurora-dsql-orms)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](https://github.com/awslabs/aurora-dsql-orms/blob/main/LICENSE)
[![PyPI - Version](https://img.shields.io/pypi/v/aurora-dsql-tortoise-orm)](https://pypi.org/project/aurora-dsql-tortoise-orm)
[![Discord chat](https://img.shields.io/discord/1435027294837276802.svg?logo=discord)](https://discord.com/invite/nEF6ksFWru)

An adapter for building [Tortoise ORM](https://tortoise.github.io/) applications with [Amazon Aurora DSQL](https://aws.amazon.com/rds/aurora/dsql/).

## Requirements

- **Tortoise ORM**: 0.25 or later
- **Python**: 3.10 or later ([installation guide](https://www.python.org/downloads/))
- **AWS Credentials**: Valid credentials configured for IAM database authentication. The adapter generates a new auth token for each connection.
- **Aerich** (optional): 0.9.2 or later, if using Aerich for migrations

## Getting Started

Install the adapter with your preferred async driver:

```bash
# asyncpg
pip install aurora-dsql-tortoise-orm[asyncpg]

# psycopg
pip install aurora-dsql-tortoise-orm[psycopg]
```

### Configuration

Configure your connection using the DSQL engine:

```python
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "aurora_dsql_tortoise.asyncpg",  # or "aurora_dsql_tortoise.psycopg"
            "credentials": {
                "host": "<cluster_id>.dsql.<region>.on.aws",
                "user": "admin",
            },
        }
    },
    "apps": {
        "models": {
            "models": ["your.models"],
            "default_connection": "default",
        }
    },
}
```

The adapter accepts all parameters supported by the underlying [asyncpg](https://magicstack.github.io/asyncpg/current/api/index.html) or [psycopg](https://www.psycopg.org/psycopg3/docs/) driver, as well as the [Aurora DSQL Connector for Python](https://github.com/awslabs/aurora-dsql-python-connector).

Or use a connection URL (requires registering the backend first):

```python
from aurora_dsql_tortoise import register_backends

register_backends()

TORTOISE_ORM = {
    "connections": {
        "default": "dsql+asyncpg://admin@<cluster_id>.dsql.<region>.on.aws/postgres"
    },
    "apps": {
        "models": {
            "models": ["your.models"],
            "default_connection": "default",
        }
    },
}
```

### Defining Models

UUID primary keys are recommended for optimal performance with Aurora DSQL:

```python
import uuid
from tortoise import fields
from tortoise.models import Model

class Owner(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "owner"
```

### Aerich Migrations

For database migrations with [Aerich](https://github.com/tortoise/aerich), include the compatibility module:

```python
TORTOISE_ORM = {
    "connections": {"default": {...}},
    "apps": {
        "models": {
            "models": [
                "your.models",
                "aerich.models",
                "aurora_dsql_tortoise.aerich_compat",
            ],
            "default_connection": "default",
        }
    },
}
```

The compatibility module patches Aerich to:
- Use UUID primary keys for migration tracking
- Execute DDL statements individually (DSQL transactions support only one DDL statement)
- Use TEXT instead of JSON column types

## Features and Limitations

- **[Adapter Behavior](docs/ADAPTER_BEHAVIOR.md)** - How the adapter modifies Tortoise ORM behavior for Aurora DSQL compatibility
- **[Known Issues](docs/KNOWN_ISSUES.md)** - Known limitations and workarounds

## Development

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
git clone https://github.com/awslabs/aurora-dsql-orms
cd aurora-dsql-orms/python/tortoise-orm
uv sync
```

### Running Tests

⚠️ Running integration tests may result in charges to your AWS account.

Unit tests:

```bash
uv run unit
```

Integration tests (requires a DSQL cluster):

```bash
cp .env.example .env
# Edit .env with your cluster endpoint
uv run integration
```

## Getting Help

- Open a support ticket with [AWS Support](http://docs.aws.amazon.com/awssupport/latest/user/getting-started.html)
- Report bugs via [GitHub Issues](https://github.com/awslabs/aurora-dsql-orms/issues/new)

## Additional Resources

- [Amazon Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html)
- [Tortoise ORM Documentation](https://tortoise.github.io/)
- [Aerich Migration Tool](https://github.com/tortoise/aerich)

## Opening Issues

If you encounter a bug, please search [existing issues](https://github.com/awslabs/aurora-dsql-orms/issues) before opening a new one. GitHub issues are intended for bug reports and feature requests.

## License

This library is licensed under the Apache 2.0 License.
