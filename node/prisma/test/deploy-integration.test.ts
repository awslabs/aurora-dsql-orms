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
  // Generated as a multi-line literal with a line that starts with BEGIN.
  note String @default("x\\nBEGIN;\\ny")
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

  async function deploy(): Promise<CommandResult> {
    const schema = `deploy_test_${process.pid}_${Date.now()}`;
    schemas.push(schema);
    return run(["prisma", "migrate", "deploy", "--config", configPath()], {
      env: {
        DEPLOY_TEST_DATABASE_URL: await databaseUrl(schema),
        PRISMA_SCHEMA_DISABLE_ADVISORY_LOCK: "1",
      },
    });
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
    // Exit 3 means fixes were applied with advisories; the file is still written.
    expect([0, 3]).toContain(generated.status);
    writeMigration(fs.readFileSync(outputFile, "utf-8"));

    const result = await deploy();

    expect(result.output).toContain("All migrations have been successfully");
    expect(result.status).toBe(0);
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
  }, 180_000);
});
