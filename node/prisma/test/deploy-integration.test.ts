/**
 * Deploy Integration Tests
 *
 * Applies generated migrations to a live Aurora DSQL cluster with the real
 * `prisma migrate deploy`. Prisma sends the file as a single query when it
 * cannot parse DSQL syntax such as `CREATE INDEX ASYNC`, so the whole file
 * runs as one transaction. Skipped unless CLUSTER_ENDPOINT is set; AWS
 * credentials must be available when it is.
 */
import { spawnSync } from "child_process";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { DsqlSigner } from "@aws-sdk/dsql-signer";
import { Client } from "pg";
import { transformMigration } from "../src/cli/transform";

const PACKAGE_ROOT = path.join(__dirname, "..");
const CLUSTER_ENDPOINT = process.env["CLUSTER_ENDPOINT"];
const describeLive = CLUSTER_ENDPOINT ? describe : describe.skip;

const SCHEMA = `datasource db {
  provider = "postgresql"
}

model Owner {
  id   String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  name String @db.VarChar(30)
  // The leading semicolon makes COMMIT resemble a standalone statement.
  note String @default("x\\n;COMMIT;\\ny")
  pets Pet[]
}

model Pet {
  id      String  @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  name    String  @db.VarChar(30)
  ownerId String? @db.Uuid
  owner   Owner?  @relation(fields: [ownerId], references: [id])

  @@index([ownerId])
}
`;

const PRISMA_CONFIG = `import * as path from "node:path";
import { defineConfig } from "prisma/config";

export default defineConfig({
  schema: path.join(__dirname, "schema.prisma"),
  migrations: { path: path.join(__dirname, "migrations") },
  datasource: { url: process.env.DEPLOY_TEST_DATABASE_URL ?? "" },
});
`;

interface CommandResult {
  status: number | null;
  stdout: string;
  output: string;
}

/** Hides the IAM auth token Prisma echoes back inside connection strings. */
function redact(text: string): string {
  return text.replace(/(postgresql:\/\/admin:)[^@\s]+/g, "$1<redacted>");
}

function run(
  args: string[],
  options: { env?: NodeJS.ProcessEnv; input?: string } = {},
): CommandResult {
  const result = spawnSync("npx", args, {
    cwd: PACKAGE_ROOT,
    encoding: "utf-8",
    env: { ...process.env, ...options.env },
    ...(options.input !== undefined && { input: options.input }),
  });
  return {
    status: result.status,
    stdout: result.stdout,
    output: redact(`${result.stdout}${result.stderr}`),
  };
}

async function databaseUrl(schema: string): Promise<string> {
  const hostname = CLUSTER_ENDPOINT!;
  const region =
    process.env["AWS_REGION"] ??
    hostname.match(/\.dsql(?:-[^.]+)?\.([a-z0-9-]+)\.on\.aws$/)?.[1];
  if (!region) {
    throw new Error(`Cannot determine the AWS region for ${hostname}`);
  }
  const signer = new DsqlSigner({ hostname, region });
  const token = encodeURIComponent(await signer.getDbConnectAdminAuthToken());
  return `postgresql://admin:${token}@${hostname}:5432/postgres?sslmode=verify-full&schema=${schema}`;
}

describeLive("prisma migrate deploy on Aurora DSQL", () => {
  let projectDir: string | undefined;
  const schemas: string[] = [];

  function configPath(): string {
    return path.join(projectDir!, "prisma.config.ts");
  }

  beforeAll(() => {
    projectDir = fs.mkdtempSync(path.join(os.tmpdir(), "prisma-deploy-"));
    fs.writeFileSync(path.join(projectDir, "schema.prisma"), SCHEMA);
    fs.writeFileSync(configPath(), PRISMA_CONFIG);
    // The config imports `prisma/config`, which resolves from node_modules.
    fs.symlinkSync(
      path.join(PACKAGE_ROOT, "node_modules"),
      path.join(projectDir, "node_modules"),
      "junction",
    );
  });

  /**
   * Drops a test schema. The drop can conflict with the asynchronous index
   * build the migration started, which DSQL reports as an optimistic
   * concurrency error (OC000 or OC001) that is safe to retry.
   */
  async function dropSchema(schema: string): Promise<CommandResult> {
    const env = { DEPLOY_TEST_DATABASE_URL: await databaseUrl(schema) };
    for (let attempt = 1; ; attempt++) {
      const result = run(
        ["prisma", "db", "execute", "--stdin", "--config", configPath()],
        { env, input: `DROP SCHEMA IF EXISTS "${schema}" CASCADE;` },
      );
      if (
        result.status === 0 ||
        attempt === 5 ||
        !/\(OC00[01]\)/.test(result.output)
      ) {
        return result;
      }
      await new Promise((resolve) => setTimeout(resolve, attempt * 2_000));
    }
  }

  afterAll(async () => {
    if (!projectDir) {
      return;
    }
    const failures: string[] = [];
    for (const schema of schemas) {
      const result = await dropSchema(schema);
      if (result.status !== 0) {
        failures.push(`${schema}: ${result.output}`);
      }
    }
    fs.rmSync(projectDir, { recursive: true, force: true });
    // Leaked schemas count toward the cluster's schema quota.
    if (failures.length > 0) {
      throw new Error(`Failed to drop test schemas:\n${failures.join("\n")}`);
    }
  }, 120_000);

  function writeMigration(sql: string): void {
    const migrations = path.join(projectDir!, "migrations");
    fs.rmSync(migrations, { recursive: true, force: true });
    fs.mkdirSync(path.join(migrations, "20260101000000_init"), {
      recursive: true,
    });
    fs.writeFileSync(
      path.join(migrations, "20260101000000_init", "migration.sql"),
      sql,
    );
    fs.writeFileSync(
      path.join(migrations, "migration_lock.toml"),
      'provider = "postgresql"\n',
    );
  }

  async function deploy(): Promise<CommandResult & { schema: string }> {
    const schema = `deploy_test_${process.pid}_${Date.now()}`;
    schemas.push(schema);
    const result = run(
      ["prisma", "migrate", "deploy", "--config", configPath()],
      {
        env: {
          DEPLOY_TEST_DATABASE_URL: await databaseUrl(schema),
          PRISMA_SCHEMA_DISABLE_ADVISORY_LOCK: "1",
        },
      },
    );
    return { ...result, schema };
  }

  async function expectDeployed(schema: string): Promise<void> {
    const client = new Client({
      connectionString: await databaseUrl(schema),
      ssl: { rejectUnauthorized: true },
    });
    await client.connect();
    try {
      const tables = await client.query(
        `SELECT tablename FROM pg_catalog.pg_tables
         WHERE schemaname = $1 AND tablename IN ('Owner', 'Pet')
         ORDER BY tablename`,
        [schema],
      );
      expect(tables.rows).toEqual([
        { tablename: "Owner" },
        { tablename: "Pet" },
      ]);
      const index = await client.query(
        `SELECT tablename, indexname, indexdef FROM pg_catalog.pg_indexes
         WHERE schemaname = $1 AND indexname = 'Pet_ownerId_idx'`,
        [schema],
      );
      expect(index.rows).toHaveLength(1);
      expect(index.rows[0]).toMatchObject({
        tablename: "Pet",
        indexname: "Pet_ownerId_idx",
      });
      expect(index.rows[0].indexdef).toMatch(/\("ownerId"\)/);
      const foreignKey = await client.query(
        `SELECT c.conname, c.convalidated, child.relname AS child,
                parent.relname AS parent,
                pg_catalog.pg_get_constraintdef(c.oid) AS definition
         FROM pg_catalog.pg_constraint c
         JOIN pg_catalog.pg_namespace n ON n.oid = c.connamespace
         JOIN pg_catalog.pg_class child ON child.oid = c.conrelid
         JOIN pg_catalog.pg_class parent ON parent.oid = c.confrelid
         WHERE n.nspname = $1 AND c.contype = 'f'
           AND c.conname = 'Pet_ownerId_fkey'`,
        [schema],
      );
      expect(foreignKey.rows).toHaveLength(1);
      expect(foreignKey.rows[0]).toMatchObject({
        conname: "Pet_ownerId_fkey",
        convalidated: false,
        child: "Pet",
        parent: "Owner",
      });
      expect(foreignKey.rows[0].definition).toMatch(
        /FOREIGN KEY \("ownerId"\)/,
      );
      expect(foreignKey.rows[0].definition).toMatch(
        /REFERENCES .*"Owner"\(id\)/,
      );
      // The test controls each generated identifier interpolated below.
      const migration = await client.query(
        `SELECT migration_name, finished_at IS NOT NULL AS finished,
                rolled_back_at IS NULL AS not_rolled_back
         FROM "${schema}"._prisma_migrations`,
      );
      expect(migration.rows).toEqual([
        {
          migration_name: "20260101000000_init",
          finished: true,
          not_rolled_back: true,
        },
      ]);
    } finally {
      await client.end();
    }
  }

  test("deploys a migration generated for a multi-statement schema", async () => {
    const outputFile = path.join(projectDir!, "generated.sql");
    const generated = run([
      "tsx",
      "src/cli/index.ts",
      "migrate",
      path.join(projectDir!, "schema.prisma"),
      "-o",
      outputFile,
    ]);
    expect(generated.status).toBe(0);
    writeMigration(fs.readFileSync(outputFile, "utf-8"));

    const result = await deploy();

    expect(result.output).toContain("All migrations have been successfully");
    expect(result.status).toBe(0);
    await expectDeployed(result.schema);
  }, 180_000);

  test("deploys a migration transformed from Prisma diff output", async () => {
    const raw = run([
      "prisma",
      "migrate",
      "diff",
      "--from-empty",
      "--to-schema",
      path.join(projectDir!, "schema.prisma"),
      "--script",
    ]);
    expect(raw.status).toBe(0);
    const inputFile = path.join(projectDir!, "raw.sql");
    const outputFile = path.join(projectDir!, "transformed.sql");
    fs.writeFileSync(inputFile, raw.stdout);
    const transformed = run([
      "tsx",
      "src/cli/index.ts",
      "transform",
      inputFile,
      "-o",
      outputFile,
    ]);
    expect(transformed.status).toBe(3);
    writeMigration(fs.readFileSync(outputFile, "utf-8"));

    const result = await deploy();
    expect(result.output).toContain("All migrations have been successfully");
    expect(result.status).toBe(0);
    await expectDeployed(result.schema);
  }, 180_000);

  test("DSQL rejects the same migration when it is not split", async () => {
    const unsplit = run([
      "prisma",
      "migrate",
      "diff",
      "--from-empty",
      "--to-schema",
      path.join(projectDir!, "schema.prisma"),
      "--script",
    ]);
    expect(unsplit.status).toBe(0);
    // The DSQL fixes without the split, as the transform produced before.
    const fixed = transformMigration(unsplit.stdout, {
      splitTransactions: false,
    });
    expect(fixed.sql).toContain("CREATE INDEX ASYNC");
    writeMigration(fixed.sql);

    const result = await deploy();

    expect(result.output).toContain(
      "multiple ddl statements not supported in a transaction",
    );
    expect(result.status).not.toBe(0);
    expect(result.output).toContain("0A000");
  }, 180_000);
});
