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

Aurora DSQL allows only one DDL statement per transaction. `prisma migrate
deploy` can send a migration file to the database as a single query, which
PostgreSQL runs as one transaction. Prisma ORM 7.3 and earlier always do this.
Later versions do it when they can't parse the file, which happens with DSQL
syntax such as `CREATE INDEX ASYNC`. The transformer splits the file and puts
each statement in its own `BEGIN`/`COMMIT` block using `dsql-lint`:

```sql
BEGIN;

CREATE TABLE "owner" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    CONSTRAINT "owner_pkey" PRIMARY KEY ("id")
);

COMMIT;

BEGIN;

CREATE INDEX ASYNC "pet_ownerId_idx" ON "pet"("ownerId");

COMMIT;
```

Each block commits on its own, so a migration is no longer atomic. If a
statement fails, the statements before it stay applied and Prisma marks the
migration as failed. Prisma may then report only `current transaction is
aborted, commands ignored until end of transaction block` instead of the
original error. To find the cause, check which blocks were applied, then run
the first block that wasn't with `psql` or `npx prisma db execute`. Fix the
cause, then [resolve the failed migration](https://pris.ly/d/migrate-resolve).
When the transform splits a file it exits with code `3` so you review this.

A file that doesn't need splitting, such as one with a single DDL statement or
only statements that change data, is left as written. In a file with DDL,
statements that change data are kept out of the transactions that contain DDL,
and statements that change data next to each other share one transaction. Put
a data change that must stay under DSQL's
[per-transaction limits](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/CHAP_quotas.html)
in its own migration.

A file that ends its own transactions with `COMMIT` or `ROLLBACK` is left as
written, except that `dsql-lint` still splits any transaction with more than
one DDL statement. Statements outside a `BEGIN`/`COMMIT` block are not
split, so in a file that manages its own transactions, put each statement in
its own block. A file that uses a setting scoped to its transaction, such as
`SET LOCAL search_path`, is also not split, because splitting it would end the
setting before the statements that rely on it run. `dsql-lint` still splits a
`BEGIN`/`COMMIT` block with more than one DDL statement, and the setting then
ends with the first block. Put each DDL statement in its own `BEGIN`/`COMMIT`
block and repeat the setting in each block.

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

Prisma generates post-creation foreign keys with `ALTER TABLE ... ADD
CONSTRAINT`. Aurora DSQL requires `NOT VALID` on these constraints, so
`dsql-lint` preserves the foreign key and adds `NOT VALID`. Add a separate
statement to validate existing rows, in its own transaction like the rest of
the transformed migration:

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
