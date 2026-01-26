# Aurora DSQL ORM Adapters

This monorepo contains ORM and database tool adapters for [Amazon Aurora DSQL](https://aws.amazon.com/rds/aurora/dsql/), AWS's distributed SQL database.

## Available Adapters

### Python

| Package | Description | PyPI | Version |
|---------|-------------|------|---------|
| [aurora-dsql-sqlalchemy](./python/sqlalchemy/) | SQLAlchemy dialect for Aurora DSQL | [PyPI](https://pypi.org/project/aurora-dsql-sqlalchemy/) | 1.1.0 |
| [aurora-dsql-tortoise-orm](./python/tortoise-orm/) | Tortoise ORM adapter for Aurora DSQL | [PyPI](https://pypi.org/project/aurora-dsql-tortoise-orm/) | 0.1.1 |

### TypeScript

*Coming soon*

### Java

*Coming soon*

## Installation

Each adapter is published as an independent package. Install the one you need:

```bash
# SQLAlchemy
pip install aurora-dsql-sqlalchemy

# Tortoise ORM
pip install aurora-dsql-tortoise-orm
```

## Documentation

See the README in each adapter's directory for detailed usage instructions:

- [SQLAlchemy adapter documentation](./python/sqlalchemy/README.md)
- [Tortoise ORM adapter documentation](./python/tortoise-orm/README.md)

## Versioning

Each adapter is versioned independently. Version numbers continue from the original standalone repositories to maintain backwards compatibility.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on how to contribute to this project.

## Security

See [CONTRIBUTING.md](./CONTRIBUTING.md#security-issue-notifications) for information on reporting security issues.

## License

This project is licensed under the Apache-2.0 License. See [LICENSE](./LICENSE) for details.
