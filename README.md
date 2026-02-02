# Aurora DSQL ORM Adapters

This monorepo contains ORM adapters for [Amazon Aurora DSQL](https://aws.amazon.com/rds/aurora/dsql/), AWS's distributed SQL database.

> **Note:** The Flyway adapter has moved to [aurora-dsql-tools](https://github.com/awslabs/aurora-dsql-tools/tree/main/flyway).

## Available Adapters

### Node.js

| Package | Description | npm | License(s) |
|---------|-------------|-----|------------|
| [@aws/aurora-dsql-prisma-tools](./node/prisma/) | CLI tools for using Prisma with Aurora DSQL | [![npm](https://img.shields.io/npm/v/@aws/aurora-dsql-prisma-tools)](https://www.npmjs.com/package/@aws/aurora-dsql-prisma-tools) | ![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg) |

### Python

| Package | Description | PyPI | License(s) |
|---------|-------------|------|------------|
| [aurora-dsql-django](./python/django/) | Django database backend for Aurora DSQL | [![PyPI](https://img.shields.io/pypi/v/aurora-dsql-django)](https://pypi.org/project/aurora-dsql-django/) | ![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg) |
| [aurora-dsql-sqlalchemy](./python/sqlalchemy/) | SQLAlchemy dialect for Aurora DSQL | [![PyPI](https://img.shields.io/pypi/v/aurora-dsql-sqlalchemy)](https://pypi.org/project/aurora-dsql-sqlalchemy/) | ![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg) |
| [aurora-dsql-tortoise-orm](./python/tortoise-orm/) | Tortoise ORM adapter for Aurora DSQL | [![PyPI](https://img.shields.io/pypi/v/aurora-dsql-tortoise-orm)](https://pypi.org/project/aurora-dsql-tortoise-orm/) | ![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg) |

### Java

| Package | Description | Maven Central | License(s) |
|---------|-------------|---------------|------------|
| [aurora-dsql-hibernate-dialect](./java/hibernate/) | Hibernate dialect for Aurora DSQL | [![Maven Central](https://img.shields.io/maven-central/v/software.amazon.dsql/aurora-dsql-hibernate-dialect)](https://central.sonatype.com/artifact/software.amazon.dsql/aurora-dsql-hibernate-dialect) | ![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg) ![License](https://img.shields.io/badge/License-LGPL_2.1-blue.svg) |

## Installation

Each adapter is published as an independent package. Install the one you need:

```bash
# Django
pip install aurora-dsql-django

# SQLAlchemy
pip install aurora-dsql-sqlalchemy

# Tortoise ORM
pip install aurora-dsql-tortoise-orm
```

For Java adapters, see the individual adapter documentation for Maven/Gradle installation instructions.

## Documentation

See the README in each adapter's directory for detailed usage instructions:

- [Django adapter documentation](./python/django/README.md)
- [Hibernate dialect documentation](./java/hibernate/README.md)
- [SQLAlchemy adapter documentation](./python/sqlalchemy/README.md)
- [Tortoise ORM adapter documentation](./python/tortoise-orm/README.md)

## Versioning

Each adapter is versioned independently. Version numbers continue from the original standalone repositories to maintain backwards compatibility.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on how to contribute to this project.

## Security

See [CONTRIBUTING.md](./CONTRIBUTING.md#security-issue-notifications) for information on reporting security issues.

## License

This repository is licensed under Apache-2.0 ([LICENSE](./LICENSE)). The Hibernate dialect has additional licensing terms; see [java/hibernate/](./java/hibernate/) for details.
