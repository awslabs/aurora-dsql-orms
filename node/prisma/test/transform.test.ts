import { transformMigration, lintMigration } from "../src/cli/transform";
import { transactionBlocks } from "./transactions";

/**
 * Shared assertion: the JSON diagnostics contain at least one entry with
 * the given fix_result.status. Replaces the old stderr-substring check.
 */
function hasDiagnosticWithStatus(
  output: ReturnType<typeof transformMigration>["output"],
  status: "fixed" | "fixed_with_warning" | "unfixable",
): boolean {
  return output.files.some((f) =>
    f.diagnostics.some((d) => d.fix_result.status === status),
  );
}

/** Leading keywords of each block, e.g. `CREATE TABLE`. */
function blockKinds(sql: string): string[] {
  return transactionBlocks(sql).map((b) => b.match(/^\w+(\s+\w+)?/)![0]);
}

describe("dsql-lint binary resolution", () => {
  // With `@aws/dsql-lint` as a package dependency, the binary is always
  // resolvable after `npm install`. We only assert the explicit override
  // path here — the "not found" path is exercised in end-to-end CI where
  // we can scrub PATH *and* the node_modules lookup, not here.
  test("throws when DSQL_LINT_PATH points to nonexistent file", () => {
    const originalPath = process.env["DSQL_LINT_PATH"];
    try {
      process.env["DSQL_LINT_PATH"] = "/nonexistent/dsql-lint";
      expect(() => transformMigration("SELECT 1;")).toThrow(/does not exist/);
    } finally {
      if (originalPath !== undefined) {
        process.env["DSQL_LINT_PATH"] = originalPath;
      } else {
        delete process.env["DSQL_LINT_PATH"];
      }
    }
  });
});

describe("Migration Transformer (dsql-lint)", () => {
  describe("basic transformations", () => {
    test("passes through clean CREATE TABLE unchanged", () => {
      const input = `CREATE TABLE "user" (
    "id" UUID NOT NULL,
    "name" VARCHAR(100),
    PRIMARY KEY ("id")
);`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).toContain('CREATE TABLE "user"');
      expect(result.sql).toContain("PRIMARY KEY");
    });

    test("handles multiple statements", () => {
      const input = `CREATE TABLE "user" (
    "id" UUID NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE "post" (
    "id" UUID NOT NULL,
    PRIMARY KEY ("id")
);`;

      const result = transformMigration(input);

      // Splitting the two statements into separate transactions is an advisory.
      expect(result.exitCode).toBe(3);
      expect(result.sql).toContain('CREATE TABLE "user"');
      expect(result.sql).toContain('CREATE TABLE "post"');
    });
  });

  describe("CREATE INDEX transformation", () => {
    test("converts CREATE INDEX to CREATE INDEX ASYNC", () => {
      const input = `CREATE INDEX "user_email_idx" ON "user"("email");`;

      const result = transformMigration(input);

      // Making an index asynchronous changes readiness semantics.
      expect(result.exitCode).toBe(3);
      expect(result.sql).toContain("CREATE INDEX ASYNC");
      expect(result.sql).not.toMatch(/CREATE\s+INDEX\s+"/);
    });

    test("converts CREATE UNIQUE INDEX to CREATE UNIQUE INDEX ASYNC", () => {
      const input = `CREATE UNIQUE INDEX "user_email_key" ON "user"("email");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(3);
      expect(result.sql).toContain("CREATE UNIQUE INDEX ASYNC");
    });

    test("does not double-convert already ASYNC indexes", () => {
      const input = `CREATE INDEX ASYNC "user_email_idx" ON "user"("email");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).not.toContain("ASYNC ASYNC");
      expect(result.sql).toContain("CREATE INDEX ASYNC");
    });

    test("handles multiple indexes", () => {
      const input = `CREATE INDEX "idx1" ON "user"("email");
CREATE INDEX "idx2" ON "user"("name");
CREATE UNIQUE INDEX "idx3" ON "user"("username");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(3);
      expect((result.sql.match(/INDEX\s+ASYNC/g) || []).length).toBe(3);
    });

    test("handles partially transformed indexes", () => {
      const input = `CREATE INDEX ASYNC "idx1" ON "user"("email");
CREATE INDEX "idx2" ON "user"("name");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(3);
      expect(result.sql).not.toContain("ASYNC ASYNC");
      expect((result.sql.match(/INDEX\s+ASYNC/g) || []).length).toBe(2);
    });
  });

  describe("foreign key validation", () => {
    test("adds NOT VALID to ALTER TABLE ADD FOREIGN KEY statements", () => {
      const input = `CREATE TABLE "post" (
    "id" UUID NOT NULL,
    "authorId" UUID NOT NULL,
    PRIMARY KEY ("id")
);

ALTER TABLE "post" ADD CONSTRAINT "post_authorId_fkey" FOREIGN KEY ("authorId") REFERENCES "user"("id");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(3);
      expect(result.sql).toContain("FOREIGN KEY");
      expect(result.sql).toContain("REFERENCES");
      expect(result.sql).toContain("NOT VALID");
      expect(hasDiagnosticWithStatus(result.output, "fixed_with_warning")).toBe(
        true,
      );
      expect(result.sql).toContain('CREATE TABLE "post"');
    });

    test("preserves supported inline REFERENCES in CREATE TABLE", () => {
      const input = `CREATE TABLE "post" (
    "id" UUID NOT NULL,
    "authorId" UUID REFERENCES "user"("id"),
    PRIMARY KEY ("id")
);`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).toContain("REFERENCES");
      expect(result.sql).toContain('CREATE TABLE "post"');
    });

    test("preserves supported cascading referential actions", () => {
      const input = `CREATE TABLE "post" (
    "authorId" UUID REFERENCES "user"("id") ON DELETE CASCADE ON UPDATE SET NULL
);`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).toContain("REFERENCES");
      expect(result.sql).toContain("ON DELETE CASCADE");
      expect(result.sql).toContain("ON UPDATE SET NULL");
      expect(result.output.summary.errors).toBe(0);
    });

    test("preserves DROP CONSTRAINT for a foreign key", () => {
      const input = `ALTER TABLE "Pet" DROP CONSTRAINT "Pet_ownerId_fkey";`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).toContain("DROP CONSTRAINT");
    });
  });

  describe("real-world Prisma output", () => {
    test("transforms typical Prisma migrate diff output", () => {
      const input = `-- CreateTable
CREATE TABLE "owner" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "name" VARCHAR(30) NOT NULL,
    "city" VARCHAR(80) NOT NULL,

    CONSTRAINT "owner_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "pet" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "name" VARCHAR(30) NOT NULL,
    "ownerId" UUID,

    CONSTRAINT "pet_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "pet_ownerId_idx" ON "pet"("ownerId");

-- AddForeignKey
ALTER TABLE "pet" ADD CONSTRAINT "pet_ownerId_fkey" FOREIGN KEY ("ownerId") REFERENCES "owner"("id") ON DELETE SET NULL ON UPDATE CASCADE;`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(3);
      expect(result.sql).toContain("CREATE INDEX ASYNC");
      expect(result.sql).toContain("FOREIGN KEY");
      expect(result.sql).toContain("REFERENCES");
      expect(result.sql).toContain("NOT VALID");
      expect(result.sql).toContain('CREATE TABLE "owner"');
      expect(result.sql).toContain('CREATE TABLE "pet"');
      expect(result.sql).toContain("gen_random_uuid()");
    });
  });

  describe("DROP statements (down migrations)", () => {
    test("preserves DROP TABLE statements", () => {
      const input = `DROP TABLE IF EXISTS "user";
DROP TABLE IF EXISTS "post";`;

      const result = transformMigration(input);

      // Splitting the two statements into separate transactions is an advisory.
      expect(result.exitCode).toBe(3);
      expect(result.sql).toContain('DROP TABLE IF EXISTS "user"');
      expect(result.sql).toContain('DROP TABLE IF EXISTS "post"');
    });

    test("preserves DROP INDEX statements", () => {
      const input = `DROP INDEX IF EXISTS "user_email_idx";`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).toContain("DROP INDEX");
    });
  });

  describe("edge cases", () => {
    test("handles empty input", () => {
      const result = transformMigration("");

      expect(result.sql.trim()).toBe("");
    });

    test("handles input with only comments", () => {
      const input = "-- This is a comment\n-- Another comment";

      const result = transformMigration(input);

      expect(result.sql.trim()).toBe("");
    });

    test("preserves non-FK ALTER TABLE statements", () => {
      const input = `ALTER TABLE "user" ADD COLUMN "email" VARCHAR(255);`;

      const result = transformMigration(input);

      expect(result.sql).toContain("ALTER TABLE");
      expect(result.sql).toContain("ADD COLUMN");
      expect(result.sql).toContain("email");
    });

    test("returns exit code 3 when adding NOT VALID to a foreign key", () => {
      const input = `ALTER TABLE "t" ADD CONSTRAINT "t_parent_fkey"
FOREIGN KEY ("parent_id") REFERENCES "parent"("id");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(3);
      expect(result.sql).toContain("NOT VALID");
      expect(hasDiagnosticWithStatus(result.output, "fixed_with_warning")).toBe(
        true,
      );
    });

    test("compound ALTER TABLE with ADD PRIMARY KEY is unfixable", () => {
      const input = `ALTER TABLE "vet" DROP CONSTRAINT "vet_pkey",
ADD COLUMN     "phone" VARCHAR(20),
ADD CONSTRAINT "vet_pkey" PRIMARY KEY ("id");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(1);
      expect(hasDiagnosticWithStatus(result.output, "unfixable")).toBe(true);
      expect(result.sql).toContain("ADD COLUMN");
      expect(result.sql).toContain("phone");
    });

    test("handles table/column names containing reserved words", () => {
      const input = `CREATE TABLE "references" ("foreign_key" VARCHAR(100));`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).toContain('CREATE TABLE "references"');
      expect(result.sql).toContain("foreign_key");
    });
  });

  describe("transaction splitting", () => {
    // `prisma migrate deploy` can send a migration file as one query, which
    // PostgreSQL runs as a single implicit transaction. DSQL allows one DDL
    // statement per transaction, so every statement needs its own.
    const prismaMigration = `-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateTable
CREATE TABLE "Owner" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    CONSTRAINT "Owner_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Pet" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "ownerId" UUID,
    CONSTRAINT "Pet_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "Pet_ownerId_idx" ON "Pet"("ownerId");

-- AddForeignKey
ALTER TABLE "Pet" ADD CONSTRAINT "Pet_ownerId_fkey" FOREIGN KEY ("ownerId") REFERENCES "Owner"("id");
`;

    test("puts each statement of a Prisma migration in its own transaction", () => {
      const result = transformMigration(prismaMigration);

      expect(blockKinds(result.sql)).toEqual([
        "CREATE SCHEMA",
        "CREATE TABLE",
        "CREATE TABLE",
        "CREATE INDEX",
        "ALTER TABLE",
      ]);
      expect(result.sql).toContain("CREATE INDEX ASYNC");
      expect(result.sql).toContain("NOT VALID");
    });

    test("reports the split as an advisory", () => {
      const result = transformMigration(
        `CREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY);`,
      );

      expect(blockKinds(result.sql)).toEqual(["CREATE TABLE", "CREATE TABLE"]);
      expect(result.exitCode).toBe(3);
      expect(result.output.summary.errors).toBe(0);
      expect(
        result.output.files[0]?.diagnostics.find(
          (d) => d.rule === "multi_ddl_transaction",
        )?.fix_result.status,
      ).toBe("fixed_with_warning");
    });

    test("splits a large migration whose lint JSON exceeds 1 MiB", () => {
      const statements = Array.from(
        { length: 5400 },
        (_, i) =>
          `CREATE TABLE "table_${i}" ("id" UUID PRIMARY KEY, "note" TEXT DEFAULT '${"x".repeat(100)}');`,
      );
      const input = statements.join("\n");
      expect(Buffer.byteLength(input)).toBeGreaterThan(900_000);
      expect(Buffer.byteLength(input)).toBeLessThan(1_000_000);

      const result = transformMigration(input);

      expect(result.exitCode).toBe(3);
      expect(Buffer.byteLength(JSON.stringify(result.output))).toBeGreaterThan(
        1024 * 1024,
      );
      expect(transactionBlocks(result.sql)).toEqual(statements);
      expect(result.sql.trimEnd()).toMatch(/COMMIT;$/);
    });

    test.each([
      ["a single statement", `CREATE TABLE "a" ("id" UUID PRIMARY KEY);`],
      [
        "data changes only",
        `INSERT INTO "a" ("id") VALUES (gen_random_uuid());\n\nINSERT INTO "a" ("id") VALUES (gen_random_uuid());`,
      ],
    ])("leaves %s as written without an advisory", (_case, sql) => {
      const result = transformMigration(sql);

      // Batches of data changes may each need their own transaction to stay
      // under DSQL's per-transaction limits.
      expect(result.sql).not.toMatch(/^(BEGIN|COMMIT);$/m);
      expect(result.sql.trim()).toBe(sql);
      expect(result.exitCode).toBe(0);
      expect(result.output.files[0]?.diagnostics).toEqual([]);
    });

    test("terminates a final statement that has no semicolon", () => {
      const result = transformMigration(
        `CREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY)`,
      );

      expect(blockKinds(result.sql)).toEqual(["CREATE TABLE", "CREATE TABLE"]);
      expect(hasDiagnosticWithStatus(result.output, "unfixable")).toBe(false);
    });

    test("keeps diagnostic line numbers aligned with the input", () => {
      const result = transformMigration(
        `-- one\nCREATE TABLE "a" ("id" UUID PRIMARY KEY);\n\n-- four\nCREATE INDEX "a_idx" ON "a"("id");`,
      );

      const index = result.output.files[0]?.diagnostics.find(
        (d) => d.rule === "index_async",
      );
      expect(index?.line).toBe(5);
    });

    test("splits DDL from DML", () => {
      const result = transformMigration(
        `CREATE TABLE "a" ("id" UUID PRIMARY KEY);\nINSERT INTO "a" ("id") VALUES (gen_random_uuid());`,
      );

      expect(blockKinds(result.sql)).toEqual(["CREATE TABLE", "INSERT INTO"]);
    });

    test("ignores transaction keywords inside comments", () => {
      const result = transformMigration(
        `-- step 1; COMMIT once reviewed\n/* step 2; COMMIT */\nCREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY);`,
      );

      expect(blockKinds(result.sql)).toEqual(["CREATE TABLE", "CREATE TABLE"]);
    });

    test.each([
      // Prisma writes a default that contains newlines as a multi-line literal.
      [
        "a COMMIT line in a string literal",
        `"note" TEXT NOT NULL DEFAULT 'x ;COMMIT\ny'`,
      ],
      ["COMMIT in a quoted column name", `"x;COMMIT" TIMESTAMP`],
      ["a column named commit", `commit TIMESTAMP`],
    ])("splits a script with %s", (_case, column) => {
      const result = transformMigration(
        `CREATE TABLE "a" (\n    "id" UUID PRIMARY KEY,\n${column}\n);\nCREATE INDEX "a_idx" ON "a"("id");`,
      );

      expect(blockKinds(result.sql)).toEqual(["CREATE TABLE", "CREATE INDEX"]);
    });

    test("is idempotent on its own output", () => {
      const first = transformMigration(prismaMigration);
      const second = transformMigration(first.sql);

      expect(second.sql).toBe(first.sql);
      expect(second.exitCode).toBe(0);
      expect(second).toEqual(expect.objectContaining({ advisories: [] }));
    });

    test.each([
      "BEGIN",
      "START TRANSACTION",
      "begin transaction",
      "/* comment */ BEGIN",
    ])(
      "does not wrap a script that already opens a transaction with %s",
      (begin) => {
        const result = transformMigration(
          `${begin};\nCREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY);\nCOMMIT;`,
        );

        // dsql-lint splits the script's own transaction. A wrapper around it
        // would leave an unmatched COMMIT after the split blocks.
        expect(result.sql.match(/^(BEGIN|START TRANSACTION)/gim)).toHaveLength(
          2,
        );
        expect(result.sql.match(/^COMMIT;$/gm)).toHaveLength(2);
      },
    );

    test("does not wrap a script that commits after its first statement", () => {
      const result = transformMigration(
        `CREATE TABLE "a" ("id" UUID PRIMARY KEY);\nBEGIN;\nINSERT INTO "c" ("n") VALUES (1);\nCOMMIT;\nCREATE TABLE "b" ("id" UUID PRIMARY KEY);`,
      );

      // Wrapping would end at the script's own COMMIT and leave an unmatched
      // COMMIT after the statements that follow it.
      expect(result.sql.match(/^BEGIN;$/gm)).toHaveLength(1);
      expect(result.sql.match(/^COMMIT;$/gm)).toHaveLength(1);
      expect(result.exitCode).toBe(3);
      expect(result).toEqual(
        expect.objectContaining({
          advisories: [expect.stringContaining("COMMIT")],
        }),
      );
    });

    test.each([
      ["COMMIT", 3],
      ["END", 3],
      ["commit", 3],
      ["end", 3],
      ["ROLLBACK", 3],
      ["ABORT", 1], // dsql-lint reports ABORT as unsupported.
    ])(
      "does not wrap a script that ends a transaction with %s",
      (end, exitCode) => {
        const input = `CREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY);\n${end};\nCREATE TABLE "c" ("id" UUID PRIMARY KEY);`;
        const result = transformMigration(input);
        const unwrapped = transformMigration(input, {
          splitTransactions: false,
        });

        expect(result.sql).not.toMatch(/^BEGIN;$/m);
        expect(result.sql).toBe(unwrapped.sql);
        expect(result.output).toEqual(unwrapped.output);
        expect(result.exitCode).toBe(exitCode);
        expect(result).toEqual(
          expect.objectContaining({
            advisories: [expect.stringContaining(String(end).toUpperCase())],
          }),
        );
        expect(unwrapped.exitCode).toBe(exitCode === 1 ? 1 : 0);
        expect(unwrapped).toEqual(expect.objectContaining({ advisories: [] }));
      },
    );

    test.each([
      [`SET LOCAL search_path TO "target"`, "SET LOCAL"],
      [`SET LOCAL ROLE "migrator"`, "SET LOCAL"],
      [`SET /* scope */ LOCAL search_path TO "target"`, "SET LOCAL"],
      [`SET -- scope\nLOCAL search_path TO "target"`, "SET LOCAL"],
      [`SET CONSTRAINTS ALL DEFERRED`, "SET CONSTRAINTS"],
      [`SELECT set_config('search_path', 'target', true)`, "set_config"],
      [
        `SELECT set_config /* scope */ ('search_path', 'target', true)`,
        "set_config",
      ],
      [`SELECT "set_config"('search_path', 'target', true)`, "set_config"],
      [
        `SELECT set_config('search_path', 'target', false), set_config('role', 'migrator', true)`,
        "set_config",
      ],
      [
        `SELECT set_config('search_path', concat(lower('x'), ''), false)`,
        "set_config",
      ],
      [`SELECT set_config('search_path', 'target', 'f')`, "set_config"],
      [
        `SELECT set_config('search_path', 'target', false::boolean)`,
        "set_config",
      ],
    ])("reports skipped splitting for %s", (setting, reason) => {
      const result = transformMigration(
        `${setting};\nCREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY);`,
      );

      // Splitting would end the setting before the tables are created.
      expect(result.sql).not.toMatch(/^(BEGIN|COMMIT);$/m);
      expect(result.exitCode).toBe(3);
      expect(result).toEqual(
        expect.objectContaining({
          advisories: [expect.stringContaining(reason)],
        }),
      );
    });

    test.each(["BEGIN", "START TRANSACTION"])(
      "does not warn about skipped wrapping when statements are framed with %s",
      (begin) => {
        const input = `-- COMMIT is in a comment, not a statement\n${begin};
SET LOCAL search_path TO "target";
CREATE TABLE "a" ("id" UUID PRIMARY KEY);
COMMIT;
${begin};
CREATE TABLE "b" ("id" UUID PRIMARY KEY);
COMMIT;`;
        const result = transformMigration(input);

        expect(result.exitCode).toBe(0);
        expect(result).toEqual(expect.objectContaining({ advisories: [] }));
        expect(
          result.sql
            .split(";")
            .map((s) => s.trim())
            .filter(Boolean),
        ).toEqual([
          begin,
          'SET LOCAL search_path TO "target"',
          'CREATE TABLE "a" ("id" UUID PRIMARY KEY)',
          "COMMIT",
          begin,
          'CREATE TABLE "b" ("id" UUID PRIMARY KEY)',
          "COMMIT",
        ]);
      },
    );

    test("does not hide an unfixable error behind a skipped-splitting advisory", () => {
      const result = transformMigration(
        `SET LOCAL search_path TO "target";
CREATE TABLE "a" ("tags" TEXT[]);
CREATE TABLE "b" ("id" UUID PRIMARY KEY);`,
      );

      expect(result.exitCode).toBe(1);
      expect(hasDiagnosticWithStatus(result.output, "unfixable")).toBe(true);
      expect(result).toEqual(
        expect.objectContaining({
          advisories: [expect.stringContaining("SET LOCAL")],
        }),
      );
    });

    test.each([
      ["a session setting", `SET search_path TO "target";`],
      ["a column named local", `UPDATE "c" SET local = 1;`],
      [
        "a string literal",
        `CREATE TABLE "c" ("n" TEXT DEFAULT 'x; SET LOCAL y');`,
      ],
      [
        "an escape string literal",
        String.raw`CREATE TABLE "c" ("n" TEXT DEFAULT E'it\'s; SET LOCAL x');`,
      ],
      [
        "a dollar-quoted body",
        `CREATE FUNCTION "f"() RETURNS INT AS $fn$ SELECT 1; SET LOCAL x = 1 $fn$ LANGUAGE sql;`,
      ],
      ["a nested comment", `/* a /* b */ SET LOCAL x = 1; */`],
    ])("splits a script that mentions SET LOCAL only in %s", (_case, sql) => {
      const result = transformMigration(
        `${sql}\nCREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY);`,
      );

      expect(blockKinds(result.sql).slice(-2)).toEqual([
        "CREATE TABLE",
        "CREATE TABLE",
      ]);
    });

    test.each([
      `SELECT pg_catalog.set_config('search_path', 'target', FALSE)`,
      `SELECT set_config('search_path'::text, current_schema()::text, false)`,
    ])("splits a script that calls set_config for the session: %s", (call) => {
      const result = transformMigration(
        `${call};\nCREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY);`,
      );

      // A session setting outlasts each transaction, so splitting keeps it.
      expect(blockKinds(result.sql).slice(-2)).toEqual([
        "CREATE TABLE",
        "CREATE TABLE",
      ]);
    });

    test("still splits a multi-DDL transaction written explicitly", () => {
      const result = transformMigration(
        `BEGIN;\nCREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY);\nCOMMIT;`,
      );

      expect(blockKinds(result.sql)).toEqual(["CREATE TABLE", "CREATE TABLE"]);
    });

    test("adds no transaction to whitespace-only input", () => {
      expect(transformMigration("  \n\n").sql.trim()).toBe("");
    });
  });

  describe("lintMigration", () => {
    test("returns exit code 0 for clean SQL", () => {
      const result = lintMigration(`CREATE TABLE "t" ("id" UUID PRIMARY KEY);`);

      expect(result.exitCode).toBe(0);
    });

    test("returns exit code 1 for SQL with issues", () => {
      const result = lintMigration(`CREATE INDEX "idx" ON "t"("col");`);

      expect(result.exitCode).toBe(1);
      expect(
        result.output.files.some((f) =>
          f.diagnostics.some((d) => d.message.includes("ASYNC")),
        ),
      ).toBe(true);
    });
  });
});
