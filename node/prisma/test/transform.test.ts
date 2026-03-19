import { Client } from "pg";
import { DsqlSigner } from "@aws-sdk/dsql-signer";
import {
  transformMigration,
  formatTransformStats,
  TransformResult,
} from "../src/cli/transform";

/**
 * Creates a pg client connected to DSQL when CLUSTER_ENDPOINT is set.
 * Returns null when no endpoint is configured (local-only unit test runs).
 */
async function connectToDsql(): Promise<Client | null> {
  const endpoint = process.env.CLUSTER_ENDPOINT;
  if (!endpoint) return null;

  const user = process.env.CLUSTER_USER ?? "admin";
  const match = endpoint.match(
    /^[a-z0-9]+\.dsql(?:-[^.]+)?\.([a-z0-9-]+)\.on\.aws$/,
  );
  if (!match?.[1]) throw new Error(`Unknown DSQL endpoint format: ${endpoint}`);

  const region = process.env.AWS_REGION ?? match[1];
  const signer = new DsqlSigner({ hostname: endpoint, region });
  const token =
    user === "admin"
      ? await signer.getDbConnectAdminAuthToken()
      : await signer.getDbConnectAuthToken();

  const client = new Client({
    host: endpoint,
    port: 5432,
    user,
    password: token,
    database: "postgres",
    ssl: true,
  });
  await client.connect();
  return client;
}

/**
 * Extracts SQL statements from transformer output, stripping BEGIN/COMMIT wrappers.
 */
function extractStatements(transformedSql: string): string[] {
  const statements: string[] = [];
  const lines = transformedSql.split("\n");
  let current = "";
  let inTransaction = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("--")) continue;
    if (trimmed === "BEGIN;") {
      inTransaction = true;
      current = "";
      continue;
    }
    if (trimmed === "COMMIT;") {
      if (current.trim()) statements.push(current.trim());
      inTransaction = false;
      current = "";
      continue;
    }
    if (inTransaction) current += (current ? "\n" : "") + line;
  }
  return statements;
}

describe("Migration Transformer", () => {
  // Connect to DSQL when CLUSTER_ENDPOINT is set, otherwise null (unit-test only)
  let dsql: Client | null = null;
  const tablesToCleanup: string[] = [];

  beforeAll(async () => {
    dsql = await connectToDsql();
  });

  afterAll(async () => {
    if (dsql) {
      for (const table of [...tablesToCleanup].reverse()) {
        await dsql.query(`DROP TABLE IF EXISTS "${table}"`).catch(() => {});
      }
      await dsql.end();
    }
  });

  /**
   * When connected to DSQL, executes each statement from the transformed SQL.
   * Registers tables for cleanup.
   */
  async function executeOnDsql(
    transformedSql: string,
    tables: string[],
  ): Promise<void> {
    if (!dsql) return;
    for (const t of tables) {
      tablesToCleanup.push(t);
      await dsql.query(`DROP TABLE IF EXISTS "${t}"`);
    }
    for (const stmt of extractStatements(transformedSql)) {
      await dsql.query(stmt);
    }
  }

  describe("basic transformations", () => {
    test("wraps single CREATE TABLE in BEGIN/COMMIT", async () => {
      const table = "dsql_test_basic_single";
      const input = `CREATE TABLE "${table}" (
    "id" UUID NOT NULL,
    "name" VARCHAR(100),
    PRIMARY KEY ("id")
);`;

      const result = transformMigration(input);

      expect(result.sql).toContain("BEGIN;");
      expect(result.sql).toContain("COMMIT;");
      expect(result.sql).toContain(`CREATE TABLE "${table}"`);
      expect(result.stats.statementsProcessed).toBe(1);

      await executeOnDsql(result.sql, [table]);
    });

    test("wraps multiple statements separately", async () => {
      const t1 = "dsql_test_basic_multi1";
      const t2 = "dsql_test_basic_multi2";
      const input = `CREATE TABLE "${t1}" (
    "id" UUID NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE "${t2}" (
    "id" UUID NOT NULL,
    PRIMARY KEY ("id")
);`;

      const result = transformMigration(input);

      const beginCount = (result.sql.match(/BEGIN;/g) || []).length;
      const commitCount = (result.sql.match(/COMMIT;/g) || []).length;

      expect(beginCount).toBe(2);
      expect(commitCount).toBe(2);
      expect(result.stats.statementsProcessed).toBe(2);

      await executeOnDsql(result.sql, [t1, t2]);
    });

    test("preserves comments before statements", async () => {
      const table = "dsql_test_basic_comments";
      const input = `-- CreateTable
CREATE TABLE "${table}" (
    "id" UUID NOT NULL,
    PRIMARY KEY ("id")
);`;

      const result = transformMigration(input);

      expect(result.sql).toContain("-- CreateTable");
      expect(result.sql).toContain("BEGIN;");

      await executeOnDsql(result.sql, [table]);
    });
  });

  describe("CREATE INDEX transformation", () => {
    test("converts CREATE INDEX to CREATE INDEX ASYNC", async () => {
      const table = "dsql_test_idx_basic";
      const input = `CREATE TABLE "${table}" (
    "id" UUID NOT NULL,
    "email" VARCHAR(255),
    PRIMARY KEY ("id")
);

CREATE INDEX "${table}_email_idx" ON "${table}"("email");`;

      const result = transformMigration(input);

      expect(result.sql).toContain("CREATE INDEX ASYNC");
      expect(result.stats.indexesConverted).toBe(1);

      await executeOnDsql(result.sql, [table]);
    });

    test("converts CREATE UNIQUE INDEX to CREATE UNIQUE INDEX ASYNC", async () => {
      const table = "dsql_test_idx_unique";
      const input = `CREATE TABLE "${table}" (
    "id" UUID NOT NULL,
    "email" VARCHAR(255),
    PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "${table}_email_key" ON "${table}"("email");`;

      const result = transformMigration(input);

      expect(result.sql).toContain("CREATE UNIQUE INDEX ASYNC");
      expect(result.stats.indexesConverted).toBe(1);

      await executeOnDsql(result.sql, [table]);
    });

    test("does not double-convert already ASYNC indexes", () => {
      const input = `CREATE INDEX ASYNC "user_email_idx" ON "user"("email");`;

      const result = transformMigration(input);

      expect(result.sql).not.toContain("ASYNC ASYNC");
      expect(result.sql).toContain("CREATE INDEX ASYNC");
      expect(result.stats.indexesConverted).toBe(0);
    });

    test("handles multiple indexes", async () => {
      const table = "dsql_test_idx_multi";
      const input = `CREATE TABLE "${table}" (
    "id" UUID NOT NULL,
    "email" VARCHAR(255),
    "name" VARCHAR(100),
    "username" VARCHAR(100),
    PRIMARY KEY ("id")
);

CREATE INDEX "${table}_idx1" ON "${table}"("email");
CREATE INDEX "${table}_idx2" ON "${table}"("name");
CREATE UNIQUE INDEX "${table}_idx3" ON "${table}"("username");`;

      const result = transformMigration(input, { includeHeader: false });

      expect(result.stats.indexesConverted).toBe(3);
      expect((result.sql.match(/INDEX\s+ASYNC/g) || []).length).toBe(3);

      await executeOnDsql(result.sql, [table]);
    });
  });

  describe("foreign key removal", () => {
    test("removes ALTER TABLE ADD FOREIGN KEY statements", async () => {
      const table = "dsql_test_fk_removal";
      const input = `CREATE TABLE "${table}" (
    "id" UUID NOT NULL,
    "authorId" UUID NOT NULL,
    PRIMARY KEY ("id")
);

ALTER TABLE "${table}" ADD CONSTRAINT "${table}_authorId_fkey" FOREIGN KEY ("authorId") REFERENCES "user"("id");`;

      const result = transformMigration(input);

      expect(result.sql).not.toContain("FOREIGN KEY");
      expect(result.sql).not.toContain("REFERENCES");
      expect(result.sql).toContain(`CREATE TABLE "${table}"`);
      expect(result.stats.foreignKeysRemoved).toBe(1);

      await executeOnDsql(result.sql, [table]);
    });

    test("removes inline REFERENCES constraints", () => {
      const input = `ALTER TABLE "post" ADD CONSTRAINT "fk_author" FOREIGN KEY ("authorId") REFERENCES "user"("id") ON DELETE CASCADE;`;

      const result = transformMigration(input);

      expect(result.sql).not.toContain("REFERENCES");
      expect(result.stats.foreignKeysRemoved).toBe(1);
    });

    test("removes DROP CONSTRAINT for foreign keys", () => {
      const input = `ALTER TABLE "Pet" DROP CONSTRAINT "Pet_ownerId_fkey";`;

      const result = transformMigration(input);

      expect(result.sql).not.toContain("DROP CONSTRAINT");
      expect(result.stats.foreignKeysRemoved).toBe(1);
    });

    test("emits warning when foreign keys are removed", () => {
      const input = `ALTER TABLE "post" ADD CONSTRAINT "fk" FOREIGN KEY ("authorId") REFERENCES "user"("id");`;

      const result = transformMigration(input);

      expect(result.warnings).toHaveLength(1);
      expect(result.warnings[0]).toContain("relationMode");
      expect(result.warnings[0]).toContain("application-layer");
    });

    test("no warning when no foreign keys present", async () => {
      const table = "dsql_test_fk_none";
      const input = `CREATE TABLE "${table}" ("id" UUID NOT NULL, PRIMARY KEY ("id"));`;

      const result = transformMigration(input);

      expect(result.warnings).toHaveLength(0);

      await executeOnDsql(result.sql, [table]);
    });
  });

  describe("SERIAL to IDENTITY conversion", () => {
    const expectedIdentity =
      "BIGINT GENERATED BY DEFAULT AS IDENTITY (CACHE 1)";

    /**
     * Executes transformed SQL on DSQL and verifies an insert with
     * auto-generated identity works. No-op when not connected.
     */
    async function verifyIdentityOnDsql(
      transformedSql: string,
      table: string,
      insertColumn: string,
      insertValue: string,
    ): Promise<void> {
      if (!dsql) return;
      await executeOnDsql(transformedSql, [table]);
      const insert = await dsql.query(
        `INSERT INTO "${table}" ("${insertColumn}") VALUES ($1) RETURNING "id"`,
        [insertValue],
      );
      expect(insert.rows[0].id).toBeDefined();
    }

    test("converts SERIAL to BIGINT IDENTITY with CACHE", async () => {
      const table = "dsql_test_serial";
      const input = `CREATE TABLE "${table}" (
    "id" SERIAL NOT NULL,
    "name" VARCHAR(100),
    CONSTRAINT "${table}_pkey" PRIMARY KEY ("id")
);`;

      const result = transformMigration(input, { includeHeader: false });

      expect(result.sql).toContain(expectedIdentity);
      expect(result.sql).not.toMatch(/\bSERIAL\b/i);
      expect(result.stats.serialTypesConverted).toBe(1);

      await verifyIdentityOnDsql(result.sql, table, "name", "Alice");
    });

    test("converts BIGSERIAL to BIGINT IDENTITY with CACHE", async () => {
      const table = "dsql_test_bigserial";
      const input = `CREATE TABLE "${table}" (
    "id" BIGSERIAL NOT NULL,
    "name" VARCHAR(100),
    CONSTRAINT "${table}_pkey" PRIMARY KEY ("id")
);`;

      const result = transformMigration(input, { includeHeader: false });

      expect(result.sql).toContain(expectedIdentity);
      expect(result.sql).not.toMatch(/\bBIGSERIAL\b/i);
      expect(result.stats.serialTypesConverted).toBe(1);

      await verifyIdentityOnDsql(result.sql, table, "name", "Bob");
    });

    test("converts SMALLSERIAL to BIGINT IDENTITY with CACHE", async () => {
      const table = "dsql_test_smallserial";
      const input = `CREATE TABLE "${table}" (
    "id" SMALLSERIAL NOT NULL,
    "name" VARCHAR(100),
    CONSTRAINT "${table}_pkey" PRIMARY KEY ("id")
);`;

      const result = transformMigration(input, { includeHeader: false });

      expect(result.sql).toContain(expectedIdentity);
      expect(result.sql).not.toMatch(/\bSMALLSERIAL\b/i);
      expect(result.stats.serialTypesConverted).toBe(1);

      await verifyIdentityOnDsql(result.sql, table, "name", "Charlie");
    });

    test("all serial variants map to BIGINT (DSQL only supports BIGINT for identity)", async () => {
      const table = "dsql_test_all_serial";
      const input = `CREATE TABLE "${table}" (
    "id" SERIAL NOT NULL,
    "seq" BIGSERIAL NOT NULL,
    "small" SMALLSERIAL NOT NULL,
    "name" VARCHAR(100),
    CONSTRAINT "${table}_pkey" PRIMARY KEY ("id")
);`;

      const result = transformMigration(input, { includeHeader: false });

      expect(result.sql).not.toContain("INTEGER GENERATED");
      expect(result.sql).not.toContain("SMALLINT GENERATED");
      const matches = result.sql.match(
        /BIGINT GENERATED BY DEFAULT AS IDENTITY \(CACHE 1\)/g,
      );
      expect(matches).toHaveLength(3);
      expect(result.stats.serialTypesConverted).toBe(3);

      if (dsql) {
        await executeOnDsql(result.sql, [table]);
        const insert = await dsql.query(
          `INSERT INTO "${table}" ("name") VALUES ($1) RETURNING "id", "seq", "small"`,
          ["test"],
        );
        expect(insert.rows[0].id).toBeDefined();
        expect(insert.rows[0].seq).toBeDefined();
        expect(insert.rows[0].small).toBeDefined();
      }
    });

    test("does not convert 'serial' in column names", async () => {
      const table = "dsql_test_serial_colname";
      const input = `CREATE TABLE "${table}" (
    "id" UUID NOT NULL,
    "serial_number" TEXT NOT NULL,
    CONSTRAINT "${table}_pkey" PRIMARY KEY ("id")
);`;

      const result = transformMigration(input, { includeHeader: false });

      expect(result.sql).toContain('"serial_number" TEXT');
      expect(result.stats.serialTypesConverted).toBe(0);

      await executeOnDsql(result.sql, [table]);
    });

    test("handles lowercase serial types", async () => {
      const table = "dsql_test_lowercase";
      const input = `CREATE TABLE "${table}" (
    "id" serial NOT NULL,
    "name" VARCHAR(100),
    CONSTRAINT "${table}_pkey" PRIMARY KEY ("id")
);`;

      const result = transformMigration(input, { includeHeader: false });

      expect(result.sql).toContain(expectedIdentity);
      expect(result.sql).not.toMatch(/\bserial\b/i);
      expect(result.stats.serialTypesConverted).toBe(1);

      await verifyIdentityOnDsql(result.sql, table, "name", "test");
    });

    test("converts SERIAL alongside other transforms (FK removal + index async)", async () => {
      const table = "dsql_test_serial_combined";
      const input = `-- CreateTable
CREATE TABLE "${table}" (
    "id" SERIAL NOT NULL,
    "userId" UUID NOT NULL,
    "total" INTEGER NOT NULL,

    CONSTRAINT "${table}_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "${table}_userId_idx" ON "${table}"("userId");

-- AddForeignKey
ALTER TABLE "${table}" ADD CONSTRAINT "${table}_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE;`;

      const result = transformMigration(input, { includeHeader: false });

      expect(result.sql).toContain(expectedIdentity);
      expect(result.sql).not.toMatch(/\bSERIAL\b/i);
      expect(result.sql).toContain("CREATE INDEX ASYNC");
      expect(result.sql).not.toContain("FOREIGN KEY");
      expect(result.stats.serialTypesConverted).toBe(1);
      expect(result.stats.indexesConverted).toBe(1);
      expect(result.stats.foreignKeysRemoved).toBe(1);
      expect(result.stats.statementsProcessed).toBe(2); // table + index, FK removed

      await executeOnDsql(result.sql, [table]);
    });
  });

  describe("identityCache option", () => {
    test("defaults to CACHE 1", () => {
      const input = `CREATE TABLE "t" ("id" SERIAL NOT NULL);`;
      const result = transformMigration(input, { includeHeader: false });
      expect(result.sql).toContain("(CACHE 1)");
    });

    test("accepts CACHE 65536", () => {
      const input = `CREATE TABLE "t" ("id" SERIAL NOT NULL);`;
      const result = transformMigration(input, {
        includeHeader: false,
        identityCache: 65536,
      });
      expect(result.sql).toContain(
        "BIGINT GENERATED BY DEFAULT AS IDENTITY (CACHE 65536)",
      );
      expect(result.sql).not.toContain("CACHE 1)");
    });

    test("accepts large CACHE values", () => {
      const input = `CREATE TABLE "t" ("id" SERIAL NOT NULL);`;
      const result = transformMigration(input, {
        includeHeader: false,
        identityCache: 100000,
      });
      expect(result.sql).toContain("(CACHE 100000)");
    });

    test("rejects CACHE values between 2 and 65535", () => {
      const input = `CREATE TABLE "t" ("id" SERIAL NOT NULL);`;
      expect(() => transformMigration(input, { identityCache: 100 })).toThrow(
        "DSQL supports CACHE = 1 or CACHE >= 65536",
      );
    });

    test("rejects CACHE 0", () => {
      const input = `CREATE TABLE "t" ("id" SERIAL NOT NULL);`;
      expect(() => transformMigration(input, { identityCache: 0 })).toThrow(
        "Must be a positive integer",
      );
    });

    test("rejects negative CACHE", () => {
      const input = `CREATE TABLE "t" ("id" SERIAL NOT NULL);`;
      expect(() => transformMigration(input, { identityCache: -1 })).toThrow(
        "Must be a positive integer",
      );
    });

    test("applies to all SERIAL variants", () => {
      const input = `CREATE TABLE "t" (
    "a" SERIAL NOT NULL,
    "b" BIGSERIAL NOT NULL,
    "c" SMALLSERIAL NOT NULL
);`;
      const result = transformMigration(input, {
        includeHeader: false,
        identityCache: 65536,
      });
      const matches = result.sql.match(
        /BIGINT GENERATED BY DEFAULT AS IDENTITY \(CACHE 65536\)/g,
      );
      expect(matches).toHaveLength(3);
    });
  });

  describe("already wrapped statements", () => {
    test("does not double-wrap statements already in BEGIN/COMMIT", async () => {
      const table = "dsql_test_wrapped";
      const input = `BEGIN;
CREATE TABLE "${table}" (
    "id" UUID NOT NULL,
    PRIMARY KEY ("id")
);
COMMIT;`;

      const result = transformMigration(input);

      const beginCount = (result.sql.match(/BEGIN;/g) || []).length;
      expect(beginCount).toBe(1);

      await executeOnDsql(result.sql, [table]);
    });
  });

  describe("DROP statements (down migrations)", () => {
    test("wraps DROP TABLE statements", async () => {
      const t1 = "dsql_test_drop1";
      const t2 = "dsql_test_drop2";

      // Create tables first so DROP works on DSQL
      if (dsql) {
        await dsql.query(
          `CREATE TABLE IF NOT EXISTS "${t1}" ("id" UUID NOT NULL, PRIMARY KEY ("id"))`,
        );
        await dsql.query(
          `CREATE TABLE IF NOT EXISTS "${t2}" ("id" UUID NOT NULL, PRIMARY KEY ("id"))`,
        );
      }

      const input = `DROP TABLE IF EXISTS "${t1}";
DROP TABLE IF EXISTS "${t2}";`;

      const result = transformMigration(input);

      expect(result.stats.statementsProcessed).toBe(2);
      expect((result.sql.match(/BEGIN;/g) || []).length).toBe(2);

      if (dsql) {
        for (const stmt of extractStatements(result.sql)) {
          await dsql.query(stmt);
        }
      }
    });

    test("wraps DROP INDEX statements", async () => {
      const input = `DROP INDEX IF EXISTS "dsql_test_nonexistent_idx";`;

      const result = transformMigration(input);

      expect(result.sql).toContain("BEGIN;");
      expect(result.sql).toContain("DROP INDEX");
      expect(result.sql).toContain("COMMIT;");

      // IF EXISTS means this is safe to run even without the index
      if (dsql) {
        for (const stmt of extractStatements(result.sql)) {
          await dsql.query(stmt);
        }
      }
    });
  });

  describe("real-world Prisma output", () => {
    test("transforms typical Prisma migrate diff output", async () => {
      const t1 = "dsql_test_rw_owner";
      const t2 = "dsql_test_rw_pet";
      const input = `-- CreateTable
CREATE TABLE "${t1}" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "name" VARCHAR(30) NOT NULL,
    "city" VARCHAR(80) NOT NULL,

    CONSTRAINT "${t1}_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "${t2}" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "name" VARCHAR(30) NOT NULL,
    "ownerId" UUID,

    CONSTRAINT "${t2}_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "${t2}_ownerId_idx" ON "${t2}"("ownerId");

-- AddForeignKey
ALTER TABLE "${t2}" ADD CONSTRAINT "${t2}_ownerId_fkey" FOREIGN KEY ("ownerId") REFERENCES "${t1}"("id") ON DELETE SET NULL ON UPDATE CASCADE;`;

      const result = transformMigration(input);

      expect(result.stats.statementsProcessed).toBe(3);
      expect(result.stats.indexesConverted).toBe(1);
      expect(result.stats.foreignKeysRemoved).toBe(1);

      expect(result.sql).toContain("-- CreateTable");
      expect(result.sql).toContain("CREATE INDEX ASYNC");
      expect(result.sql).not.toContain("FOREIGN KEY");
      expect(result.sql).not.toContain("AddForeignKey");

      await executeOnDsql(result.sql, [t2, t1]);
    });
  });

  describe("header comment", () => {
    test("includes header by default", () => {
      const input = `CREATE TABLE "user" ("id" UUID);`;

      const result = transformMigration(input);

      expect(result.sql).toContain("Transformed for Aurora DSQL");
    });

    test("can exclude header", () => {
      const input = `CREATE TABLE "user" ("id" UUID);`;

      const result = transformMigration(input, { includeHeader: false });

      expect(result.sql).not.toContain("Transformed for Aurora DSQL");
    });
  });

  describe("formatTransformStats", () => {
    test("formats stats correctly", () => {
      const stats: TransformResult["stats"] = {
        statementsProcessed: 5,
        indexesConverted: 2,
        foreignKeysRemoved: 1,
        serialTypesConverted: 0,
      };

      const output = formatTransformStats(stats);

      expect(output).toContain("5 statement(s)");
      expect(output).toContain("2 index(es)");
      expect(output).toContain("1 foreign key");
    });

    test("omits zero counts", () => {
      const stats: TransformResult["stats"] = {
        statementsProcessed: 3,
        indexesConverted: 0,
        foreignKeysRemoved: 0,
        serialTypesConverted: 0,
      };

      const output = formatTransformStats(stats);

      expect(output).toContain("3 statement(s)");
      expect(output).not.toContain("index");
      expect(output).not.toContain("foreign key");
      expect(output).not.toContain("SERIAL");
    });

    test("includes SERIAL conversion count", () => {
      const stats: TransformResult["stats"] = {
        statementsProcessed: 1,
        indexesConverted: 0,
        foreignKeysRemoved: 0,
        serialTypesConverted: 2,
      };

      const output = formatTransformStats(stats);

      expect(output).toContain("2 SERIAL type(s) to IDENTITY");
    });

    test("includes warnings when provided", () => {
      const stats: TransformResult["stats"] = {
        statementsProcessed: 1,
        indexesConverted: 0,
        foreignKeysRemoved: 1,
        serialTypesConverted: 0,
      };
      const warnings = ["Test warning message"];

      const output = formatTransformStats(stats, warnings);

      expect(output).toContain("⚠ Test warning message");
    });
  });

  describe("edge cases", () => {
    test("handles empty input", () => {
      const result = transformMigration("");

      expect(result.sql.trim()).toBe("");
      expect(result.stats.statementsProcessed).toBe(0);
    });

    test("handles input with only comments", () => {
      const input = "-- This is a comment\n-- Another comment";

      const result = transformMigration(input);

      expect(result.stats.statementsProcessed).toBe(0);
    });

    test("handles statements without trailing semicolon", async () => {
      const table = "dsql_test_edge_nosemicolon";
      const input = `CREATE TABLE "${table}" ("id" UUID NOT NULL, PRIMARY KEY ("id"))`;

      const result = transformMigration(input);

      expect(result.sql).toContain("BEGIN;");
      expect(result.sql).toContain("COMMIT;");
      // Should add semicolon
      expect(result.sql).toMatch(/\);?\s*\nCOMMIT;/);

      await executeOnDsql(result.sql, [table]);
    });

    test("handles mixed wrapped and unwrapped statements", async () => {
      const t1 = "dsql_test_edge_mixed1";
      const t2 = "dsql_test_edge_mixed2";
      const input = `BEGIN;
CREATE TABLE "${t1}" ("id" UUID NOT NULL, PRIMARY KEY ("id"));
COMMIT;

CREATE TABLE "${t2}" ("id" UUID NOT NULL, PRIMARY KEY ("id"));`;

      const result = transformMigration(input, { includeHeader: false });

      // Should have 2 statements total
      expect(result.stats.statementsProcessed).toBe(2);
      // Should have 2 BEGIN/COMMIT pairs (one original, one added)
      expect((result.sql.match(/BEGIN;/g) || []).length).toBe(2);

      await executeOnDsql(result.sql, [t1, t2]);
    });

    test("handles partially transformed indexes", () => {
      const input = `CREATE INDEX ASYNC "idx1" ON "user"("email");
CREATE INDEX "idx2" ON "user"("name");`;

      const result = transformMigration(input, { includeHeader: false });

      // Only idx2 should be converted
      expect(result.stats.indexesConverted).toBe(1);
      // Both should be wrapped
      expect(result.stats.statementsProcessed).toBe(2);
    });

    test("preserves non-FK ALTER TABLE statements", async () => {
      const table = "dsql_test_edge_alter";
      // Create the table first so ALTER TABLE works on DSQL
      if (dsql) {
        tablesToCleanup.push(table);
        await dsql.query(`DROP TABLE IF EXISTS "${table}"`);
        await dsql.query(
          `CREATE TABLE "${table}" ("id" UUID NOT NULL, PRIMARY KEY ("id"))`,
        );
      }

      const input = `ALTER TABLE "${table}" ADD COLUMN "email" VARCHAR(255);`;

      const result = transformMigration(input, { includeHeader: false });

      expect(result.sql).toContain("ALTER TABLE");
      expect(result.sql).toContain("ADD COLUMN");
      expect(result.stats.statementsProcessed).toBe(1);
      expect(result.stats.foreignKeysRemoved).toBe(0);

      if (dsql) {
        for (const stmt of extractStatements(result.sql)) {
          await dsql.query(stmt);
        }
      }
    });

    test("handles compound ALTER TABLE with DROP/ADD CONSTRAINT for pkey", () => {
      // Prisma generates this when comparing against live database
      const input = `ALTER TABLE "vet" DROP CONSTRAINT "vet_pkey",
ADD COLUMN     "phone" VARCHAR(20),
ADD CONSTRAINT "vet_pkey" PRIMARY KEY ("id");`;

      // Without --force, should report unsupported statements
      // ADD CONSTRAINT for same PK is also skipped (paired with DROP)
      const result = transformMigration(input, { includeHeader: false });

      expect(result.unsupportedStatements).toHaveLength(1);
      expect(result.unsupportedStatements[0]).toContain("DROP CONSTRAINT");
      // Only ADD COLUMN should be in output (ADD CONSTRAINT skipped since paired with DROP)
      expect(result.sql).toContain("ADD COLUMN");
      expect(result.sql).not.toContain("ADD CONSTRAINT");
      expect(result.sql).not.toContain("PRIMARY KEY");
    });

    test("with --force, removes DROP/ADD CONSTRAINT and keeps ADD COLUMN", () => {
      const input = `ALTER TABLE "vet" DROP CONSTRAINT "vet_pkey",
ADD COLUMN     "phone" VARCHAR(20),
ADD CONSTRAINT "vet_pkey" PRIMARY KEY ("id");`;

      const result = transformMigration(input, {
        includeHeader: false,
        force: true,
      });

      // Should keep ADD COLUMN but remove DROP/ADD CONSTRAINT
      expect(result.sql).toContain("ADD COLUMN");
      expect(result.sql).toContain("phone");
      expect(result.sql).not.toContain("DROP CONSTRAINT");
      expect(result.sql).not.toContain("PRIMARY KEY");
      expect(result.stats.statementsProcessed).toBe(1);
      expect(result.unsupportedStatements).toHaveLength(1); // Still tracked
    });

    test("removes empty ALTER TABLE after filtering with --force", () => {
      // If only DROP/ADD CONSTRAINT, statement should be removed entirely
      const input = `ALTER TABLE "vet" DROP CONSTRAINT "vet_pkey",
ADD CONSTRAINT "vet_pkey" PRIMARY KEY ("id");`;

      const result = transformMigration(input, {
        includeHeader: false,
        force: true,
      });

      expect(result.sql.trim()).toBe("");
      expect(result.stats.statementsProcessed).toBe(0);
    });

    test("without --force, skips paired ADD CONSTRAINT", () => {
      // Without force, we skip ADD CONSTRAINT that's paired with DROP
      // This avoids outputting partial SQL that would fail anyway
      const input = `ALTER TABLE "vet" DROP CONSTRAINT "vet_pkey",
ADD CONSTRAINT "vet_pkey" PRIMARY KEY ("id");`;

      const result = transformMigration(input, { includeHeader: false });

      // DROP is tracked as unsupported
      expect(result.unsupportedStatements).toHaveLength(1);
      // Statement is empty after filtering, so nothing in output
      expect(result.sql.trim()).toBe("");
      expect(result.stats.statementsProcessed).toBe(0);
    });

    test("handles table/column names containing reserved words", async () => {
      const table = "dsql_test_edge_reserved";
      const input = `CREATE TABLE "${table}" ("id" UUID NOT NULL, "foreign_key" VARCHAR(100), PRIMARY KEY ("id"));`;

      const result = transformMigration(input, { includeHeader: false });

      // Should NOT be removed - it's a table, not an FK constraint
      expect(result.sql).toContain(`CREATE TABLE "${table}"`);
      expect(result.stats.statementsProcessed).toBe(1);
      expect(result.stats.foreignKeysRemoved).toBe(0);

      await executeOnDsql(result.sql, [table]);
    });
  });
});
