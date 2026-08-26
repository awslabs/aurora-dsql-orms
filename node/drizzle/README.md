# Aurora DSQL adapter for Drizzle ORM

[![GitHub](https://img.shields.io/badge/github-awslabs/aurora--dsql--orms-blue?logo=github)](https://github.com/awslabs/aurora-dsql-orms)
[![npm version](https://img.shields.io/npm/v/@aws/aurora-dsql-drizzle.svg)](https://www.npmjs.com/package/@aws/aurora-dsql-drizzle)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Discord chat](https://img.shields.io/discord/1435027294837276802.svg?logo=discord)](https://discord.com/invite/nEF6ksFWru)

[Drizzle ORM](https://orm.drizzle.team/) support for [Amazon Aurora DSQL](https://aws.amazon.com/rds/aurora/dsql/).

It rides on `drizzle-orm/node-postgres`: the [Aurora DSQL connector](https://github.com/awslabs/aurora-dsql-connectors/tree/main/node/node-postgres) is a `pg.Pool` with IAM token authentication, so there is no custom dialect — just a thin `drizzle()` factory, an opt-in OCC retry helper, a DSQL-aware migrator, and a migration CLI.

## Requirements

- Drizzle ORM `^0.45` and `pg` `>=8` (peer dependencies)
- Node.js `>=20`
- An Aurora DSQL cluster, and AWS credentials with `dsql:DbConnect` for the database role you connect as

## Install

```bash
npm install @aws/aurora-dsql-drizzle drizzle-orm pg
npm install -D drizzle-kit
```

IAM authentication and TLS are handled by the connector.

## Connect

```ts
import { drizzle } from "@aws/aurora-dsql-drizzle";
import * as schema from "./schema";

const db = drizzle({
  connection: {
    host: process.env.CLUSTER_ENDPOINT!, // <id>.dsql.<region>.on.aws
    region: "us-east-1", // optional; inferred from the host otherwise
    user: "myuser", // a database role scoped to what your app needs
    options: "-c search_path=myschema",
  },
  schema,
});

const owners = await db.select().from(schema.owner);
```

`user` is required — see [Using database roles and IAM authentication](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html) for creating a role granted only the privileges your application needs. There is no default, so a connection never lands on `admin` by omission.

Already have a pool? Pass it directly: `drizzle({ client: pool, schema })`, where `pool` is an `AuroraDSQLPool` (or any `pg.Pool`). `db.$client` exposes the underlying pool; call `await db.$client.end()` to close it.

## Transactions with OCC retry

DSQL uses optimistic concurrency control: conflicting transactions fail at COMMIT with `OC000` / `OC001` (SQLSTATE `40001`). `db.transactionWithRetry` re-runs the whole transaction on those conflicts.

```ts
import { sql } from "drizzle-orm";

await db.transactionWithRetry(async (tx) => {
  await tx.update(accounts).set({ balance: sql`balance - 100` }).where(...);
  await tx.update(accounts).set({ balance: sql`balance + 100` }).where(...);
});
```

The callback is re-run on every retry, so it **must be idempotent** — no side effects (emails, queue writes) that must not repeat. Keep transactions flat: a nested `tx.transaction()` fails fast with an explanatory error, so partial work is never mistaken for a committed savepoint.

Retry defaults are `maxRetries` 3, `baseDelayMs` 50, `maxDelayMs` 5000 (exponential backoff with equal jitter). Pass an optional transaction config second and retry overrides third; when retries are exhausted it throws `AwsDsqlRetryExhaustedError` (the last conflict is on `.cause`).

```ts
await db.transactionWithRetry(
  async (tx) => { await tx.insert(orders).values({ ... }); },
  { isolationLevel: "serializable" },
  { maxRetries: 5, onRetry: (err, attempt, max) => log.warn({ err, attempt, max }) },
);
```

## Migrations

Import `migrate` from this package. It applies one DDL statement per transaction — matching how DSQL runs DDL — and tracks each statement individually, so use it in place of the stock `drizzle-orm/node-postgres` migrator, which sends every statement in a single transaction:

```ts
import { migrate, getMigrationStatus } from "@aws/aurora-dsql-drizzle";

const result = await migrate(db, { migrationsFolder: "./drizzle" });
if (!result.success) throw new Error(result.error.message);
```

The workflow is:

1. **Generate** SQL from your schema and rewrite it for DSQL:

   ```bash
   npx aurora-dsql-drizzle generate --out ./drizzle -- --config drizzle.config.ts
   ```

   This runs `drizzle-kit generate`, then rewrites each statement with [`dsql-lint`](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint) — the Aurora DSQL linter and fixer — while preserving Drizzle's `--> statement-breakpoint` markers. It turns `CREATE INDEX` into `CREATE INDEX ASYNC`, rewrites `SERIAL` columns as `BIGINT … GENERATED … AS IDENTITY` (a type widening — review it), and adds `NOT VALID` to foreign keys created with `ALTER TABLE`. Review and commit the result. (`transform` and `lint` subcommands run those steps on their own.)

   For every post-creation foreign key, add a separate `ALTER TABLE ASYNC
... VALIDATE CONSTRAINT ...` statement after the transformed `NOT VALID`
   statement. The constraint applies to new writes immediately; the validation
   job checks existing rows. The migrator waits for that asynchronous job.

   Aurora DSQL supports `NO ACTION`, `RESTRICT`, `CASCADE`, `SET NULL`, and
   `SET DEFAULT`, plus `MATCH SIMPLE`, `MATCH FULL`, and deferrable foreign
   keys. Cascading actions count toward transaction row-modification limits.
   Prefer `NO ACTION` or `RESTRICT` for unbounded child cardinality and use
   transaction retry handling because foreign-key conflicts can surface as
   serialization failures.

   Keep Drizzle Kit's `breakpoints: true` (the default). The adapter applies one statement per marker, so a breakpoint-free file holding more than one statement is rejected with an explanatory error rather than sent as a single multi-statement transaction.

   Known limitation: the transform lints each statement separately, so a fix needing more than one statement at a time does not apply. The case to know about is `ALTER COLUMN … ADD GENERATED … AS IDENTITY`, which `dsql-lint` folds into the preceding `CREATE TABLE` when it sees both together; here it sees only the `ALTER` and reports it as unfixable. Define identity columns in the table definition, or merge the two statements by hand.

2. **Apply** the committed migrations at deploy time, using the `migrate()` call above.

   Each statement is applied on its own (autocommit) and then recorded in a tracking table, so a run interrupted partway resumes where it left off — recorded statements are skipped. Asynchronous DDL (`CREATE INDEX ASYNC`, `ALTER TABLE ASYNC … VALIDATE CONSTRAINT`) is awaited before the statement is recorded, so a failed background job is never reported as success. Conflicting statements are retried on DSQL's optimistic-concurrency errors. `getMigrationStatus(db, config)` reports applied vs. pending without changing anything.

   One caveat on resuming: a statement and its tracking row are separate commits. If a run dies in the gap between them, the statement is applied but untracked, and because `drizzle-kit` emits `CREATE TABLE` without `IF NOT EXISTS` the re-run fails with "already exists". `migrate()` reports which statement it was so you can reconcile the tracking table by hand.

## CLI

```
aurora-dsql-drizzle generate [--out <dir>] [-- <drizzle-kit args>]   Generate + transform
aurora-dsql-drizzle transform [input] [-o output]                    Transform SQL for DSQL
aurora-dsql-drizzle lint [input]                                      Lint SQL for DSQL
```

Exit codes: `0` clean, `1` unfixable errors remain (and the adapter's own usage errors, e.g. an unknown flag), `2` usage error propagated from dsql-lint, `3` fixed with advisories (e.g. `NOT VALID` added to a foreign key — add asynchronous validation before applying).

## Example

See [examples/veterinary-app](./examples/veterinary-app/) for a complete project: schema, committed DSQL migration, `db:migrate` script, and integration tests against a live cluster.

## Resources

- [Amazon Aurora DSQL documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html)
- [Unsupported PostgreSQL features in DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-unsupported-features.html)
- [Aurora DSQL connector for node-postgres](https://github.com/awslabs/aurora-dsql-connectors/tree/main/node/node-postgres)
- [Drizzle ORM documentation](https://orm.drizzle.team/docs)
- [dsql-lint](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint)

## Security

See [CONTRIBUTING](../../CONTRIBUTING.md#security-issue-notifications) for more information.

## License

Apache-2.0
