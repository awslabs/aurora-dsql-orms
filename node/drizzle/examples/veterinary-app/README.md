# Veterinary app (Drizzle + Aurora DSQL)

A small veterinary clinic schema demonstrating [@aws/aurora-dsql-drizzle](../../): IAM-authenticated connections, DSQL-ready migrations, and relational queries.

## Layout

- `src/schema.ts` — Drizzle tables. UUID primary keys, and relationships declared at the ORM level with `relations()` rather than `references()`, so the generated SQL carries no foreign-key constraints
- `drizzle/` — the committed migration, generated with `drizzle-kit` and rewritten for DSQL (`CREATE INDEX ASYNC`, `USING btree` removed)
- `src/dsql-client.ts` — builds the `drizzle()` database
- `src/migrate.ts` — applies migrations via the adapter's `migrate()`
- `src/example.ts` — populates and verifies data

## Run

```bash
export CLUSTER_ENDPOINT=<your-cluster-id>.dsql.<region>.on.aws
export CLUSTER_USER=myuser   # required; the database role to connect as

npm install
npm run db:migrate   # applies drizzle/ with the adapter's migrate()
npm run sample       # populate + verify
npm test             # integration tests (needs the cluster)
```

Credentials come from the default AWS credential chain, and need `dsql:DbConnect` for the role named in `CLUSTER_USER`.

### Setting up the database role

Connect as `admin` once to create an application role scoped to just this app's schema. See [Using database roles and IAM authentication](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html):

```sql
CREATE SCHEMA myschema;
CREATE ROLE myuser WITH LOGIN;
AWS IAM GRANT myuser TO 'arn:aws:iam::<account-id>:role/<your-iam-role>';
GRANT USAGE, CREATE ON SCHEMA myschema TO myuser;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA myschema TO myuser;
```

`CLUSTER_USER=myuser` makes the app connect with `search_path=myschema`. There is no default, so the app never lands on `admin` and the shared `public` schema by omission; `CLUSTER_USER=admin` still works if you want that for a first run.

Note that `migrate()` creates its own tracking schema, so the role running migrations needs schema-creation privileges. A common split is to run `db:migrate` with an elevated identity during deployment and run the application itself as the scoped role.

## Regenerating the migration

After changing `src/schema.ts`:

```bash
npm run db:generate   # aurora-dsql-drizzle generate: drizzle-kit generate + dsql-lint --fix
```

This is the adapter's own CLI wrapping both steps, so plain `drizzle-kit generate` isn't needed — the second step is what rewrites the generated SQL for DSQL. Review and commit the result.
