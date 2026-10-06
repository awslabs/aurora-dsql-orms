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

`@aws/dsql-lint` is included using npm's `latest` dist-tag and uses its bundled
binary by default (no setup required). Fresh dependency resolution installs the
current release; existing lockfiles keep their recorded version until the
dependency is updated or the lockfile is regenerated. To use a custom or
existing installation, set `DSQL_LINT_PATH`.

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

The validator generates SQL from your schema and delegates compatibility checks
to [`dsql-lint --fix`](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint),
the same path used to transform migrations. Transformable SQL passes validation
with advisories; unfixable SQL fails. `relationMode = "prisma"` remains useful
for automated migrations, but is no longer mandatory.

#### Example Output

```
⚠ Column `"id"` uses SERIAL, which is not supported in DSQL.
  → Replaced SERIAL with a DSQL-compatible identity column.

✓ Validation passed with 1 advisory
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

#### Transactions

Aurora DSQL allows one DDL statement per transaction. `transform` puts DDL
statements in separate `BEGIN`/`COMMIT` blocks for `prisma migrate deploy`, which
can run a file as one transaction. Data changes run separately from DDL;
adjacent data changes share a transaction. Keep large data changes in separate
migrations within DSQL's [transaction limits](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/CHAP_quotas.html).

If a statement fails, earlier committed changes remain applied. If Prisma reports
only `current transaction is aborted`, run the first unapplied block with `psql`
or `npx prisma db execute` to find the cause. Fix it, then
[resolve the failed migration](https://pris.ly/d/migrate-resolve).

Splitting produces an advisory: `transform` writes the SQL and exits with code
`3`; `migrate` logs the advisory and exits with code `0`.

Single-statement and data-only files do not need splitting.
For files containing `COMMIT`, `ROLLBACK`, or transaction-scoped settings such
as `SET LOCAL`, put each DDL statement in its own transaction and repeat any
required settings. `transform` does not add transaction blocks to these files,
but `dsql-lint` can split existing blocks, ending their transaction-scoped settings.

For hand-written migrations, put each `CREATE ROLE`, `CREATE DOMAIN`, `GRANT`,
or `COMMENT ON` statement in its own `BEGIN`/`COMMIT` block. `dsql-lint` does
not split these statements into separate transactions.

### Lint Migrations

Check a SQL migration file for DSQL compatibility without applying fixes:

```bash
npx aurora-dsql-prisma lint migration.sql
```

Use `transform` before deployment: `lint` checks SQL compatibility but does not
account for Prisma running the file as one transaction.

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

Prisma generates post-creation foreign keys with `ALTER TABLE ... ADD
CONSTRAINT`. Aurora DSQL requires `NOT VALID` on these constraints, so
`dsql-lint` preserves the foreign key and adds `NOT VALID`. After running
`transform`, add the following block to validate existing rows, or put it in
a separate migration. Adding it before transformation prevents the transformer
from wrapping the remaining statements:

```sql
BEGIN;
ALTER TABLE ASYNC "table_name" VALIDATE CONSTRAINT "constraint_name";
COMMIT;
```

The transform exits with code `3` to ensure you review and add the validation
statement. The constraint applies to new writes immediately, but existing rows
remain unvalidated until the asynchronous job completes.

## Prisma Schema Requirements

When using Prisma with Aurora DSQL:

1. **Choose a relation mode**:

   ```prisma
   datasource db {
     provider     = "postgresql"
     relationMode = "prisma"
   }
   ```

   Use `relationMode = "prisma"` when the application should emulate
   referential integrity. To use native DSQL foreign keys, omit it. Aurora DSQL
   supports `NoAction`, `Restrict`, `Cascade`, `SetNull`, and `SetDefault`.
   Post-creation constraints are transformed to `NOT VALID`; add the
   corresponding `ALTER TABLE ASYNC ... VALIDATE CONSTRAINT` statement before
   applying the migration.

   Cascading actions count toward Aurora DSQL's transaction row-modification
   limits. Prefer `NoAction` or `Restrict` where child-row cardinality is
   unbounded, and run transactions through retry handling because foreign-key
   conflicts can surface as serialization failures.

2. **Use UUID for IDs**:

   ```prisma
   model User {
     id String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
   }
   ```

3. **Disable advisory locks** - When running migrations:
   ```bash
   PRISMA_SCHEMA_DISABLE_ADVISORY_LOCK=1 npx prisma migrate deploy
   ```

For the full list of Aurora DSQL SQL compatibility details, see the [PostgreSQL compatibility reference](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html).

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
