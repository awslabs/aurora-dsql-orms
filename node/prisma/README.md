# Aurora DSQL Tools for Prisma

[![GitHub](https://img.shields.io/badge/github-awslabs/aurora--dsql--orms-blue?logo=github)](https://github.com/awslabs/aurora-dsql-orms)
[![npm version](https://img.shields.io/npm/v/@aws/aurora-dsql-prisma-tools.svg)](https://www.npmjs.com/package/@aws/aurora-dsql-prisma-tools)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Discord chat](https://img.shields.io/discord/1435027294837276802.svg?logo=discord)](https://discord.com/invite/nEF6ksFWru)

CLI tools for using [Prisma ORM](https://www.prisma.io/) with [Amazon Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html).

## Overview

This package provides:

1. **Schema Validator** - Validates Prisma schemas for DSQL compatibility
2. **Migration Transformer** - Converts Prisma migrations to DSQL-compatible SQL using [`dsql-lint`](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint)
3. **Migration Linter** - Checks SQL migrations for DSQL compatibility without modifying them
4. **All-in-one Migrate Command** - Validates, generates, and transforms in one step

Aurora DSQL has [specific PostgreSQL compatibility limitations](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-unsupported-features.html). These tools help you catch issues early and automate the required transformations.

## Installation

```bash
npm install --save-dev @aws/aurora-dsql-prisma-tools
```

**Supported Node.js versions:** 20+ (Active and LTS releases)

`@aws/dsql-lint` is pulled in automatically as a dependency — the prebuilt native binary that ships with it is used at runtime, so there's no additional setup. If you prefer an existing installation (`cargo install dsql-lint`) or a custom path, set the `DSQL_LINT_PATH` environment variable and it will take precedence.

## Quick Start

Generate a DSQL-compatible migration in one command:

```bash
npx aurora-dsql-prisma migrate prisma/schema.prisma -o prisma/migrations/001_init/migration.sql
```

If validation fails, fix your schema and re-run.

## Commands

### Validate Schema

Check your Prisma schema for DSQL compatibility before runtime:

```bash
npx aurora-dsql-prisma validate prisma/schema.prisma
```

#### What the Validator Checks

The validator checks that `relationMode = "prisma"` is set in the datasource block (DSQL does not support foreign keys). All other SQL compatibility checks are delegated to [`dsql-lint`](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint) — the validator generates SQL from your schema and lints it. See the [dsql-lint README](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint) for the full list of rules.

#### Example Output

```
✗ Missing relationMode = "prisma" in datasource block (line 1)
  → Add relationMode = "prisma" to your datasource block. DSQL does not support foreign key constraints.
✗ Column `"id"` uses SERIAL, which is not supported in DSQL.

✗ Validation failed: 2 error(s)
```

### Transform Migrations

Transform Prisma-generated migrations to be DSQL-compatible:

```bash
# Transform from file
npx aurora-dsql-prisma transform raw.sql -o migration.sql

# Transform using pipes (stdin)
npx prisma migrate diff \
    --from-empty \
    --to-schema prisma/schema.prisma \
    --script | npx aurora-dsql-prisma transform > migration.sql
```

#### What the Transformer Does

The transform command uses [`dsql-lint --fix`](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint) to apply DSQL compatibility fixes. See the [dsql-lint README](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint) for the full list of rules and transformations.

### Lint Migrations

Check a SQL migration file for DSQL compatibility without applying fixes:

```bash
npx aurora-dsql-prisma lint migration.sql
```

### All-in-One Migrate

Validate, generate, and transform in one step:

```bash
npx aurora-dsql-prisma migrate prisma/schema.prisma -o prisma/migrations/001_init/migration.sql
```

For incremental migrations against an existing database:

```bash
npx aurora-dsql-prisma migrate prisma/schema.prisma \
    -o prisma/migrations/002_add_column/migration.sql \
    --from-config-datasource
```

## Incremental Migrations

After your initial deployment, use `--from-config-datasource` to generate migrations that only include differences from the live database:

```bash
npx aurora-dsql-prisma migrate prisma/schema.prisma \
    -o prisma/migrations/002_add_email/migration.sql \
    --from-config-datasource
```

This requires a `prisma.config.ts` that provides database credentials. See the [example](examples/veterinary-app/) for a working implementation.

### Handling Unsupported Statements

Sometimes Prisma generates `DROP CONSTRAINT` statements when comparing against a live database. DSQL doesn't support `DROP CONSTRAINT`. If `dsql-lint` reports unfixable errors, review its output and manually adjust the migration.

## Prisma Schema Requirements

When using Prisma with Aurora DSQL:

1. **Set relation mode** - DSQL doesn't support foreign keys:

   ```prisma
   datasource db {
     provider     = "postgresql"
     relationMode = "prisma"
   }
   ```

2. **Use UUID for IDs** - DSQL doesn't support sequences:

   ```prisma
   model User {
     id String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
   }
   ```

3. **Disable advisory locks** - When running migrations:
   ```bash
   PRISMA_SCHEMA_DISABLE_ADVISORY_LOCK=1 npx prisma migrate deploy
   ```

## Example

See [examples/veterinary-app/](examples/veterinary-app/) for a complete working example including:

- DSQL-compatible Prisma schema
- DsqlPrismaClient with automatic IAM authentication
- Sample CRUD operations
- Integration tests

## Additional Resources

- [Amazon Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html)
- [Unsupported PostgreSQL Features in DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-unsupported-features.html)
- [Aurora DSQL Connector for node-postgres](https://github.com/awslabs/aurora-dsql-connectors/tree/main/node/node-postgres/)
- [Prisma Documentation](https://www.prisma.io/docs)
- [Prisma Relation Mode](https://www.prisma.io/docs/orm/prisma-schema/data-model/relations/relation-mode)

## Security

See [CONTRIBUTING](../../CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
