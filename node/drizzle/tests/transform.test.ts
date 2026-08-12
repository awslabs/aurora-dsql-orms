import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  transformMigration,
  lintMigration,
  transformMigrationFile,
  worseExitCode,
} from "../src/cli/transform";

/**
 * Shared assertion: the JSON diagnostics contain at least one entry with
 * the given fix_result.status.
 */
function hasDiagnosticWithStatus(
  output: ReturnType<typeof transformMigration>["output"],
  status: "fixed" | "fixed_with_warning" | "unfixable",
): boolean {
  return output.files.some((f) =>
    f.diagnostics.some((d) => d.fix_result.status === status),
  );
}

describe("dsql-lint binary resolution", () => {
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

// Stands in for the dsql-lint binary with a script that prints `stdout`, so the
// guards on its wire format can be driven with output a real run won't produce.
function withFakeDsqlLint(stdout: string, assert: () => void): void {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "fake-dsql-lint-"));
  const binary = path.join(dir, "dsql-lint");
  fs.writeFileSync(
    binary,
    `#!/usr/bin/env node\nprocess.stdout.write(${JSON.stringify(stdout)});\n`,
    { mode: 0o755 },
  );
  const originalPath = process.env["DSQL_LINT_PATH"];
  process.env["DSQL_LINT_PATH"] = binary;
  try {
    assert();
  } finally {
    if (originalPath !== undefined) {
      process.env["DSQL_LINT_PATH"] = originalPath;
    } else {
      delete process.env["DSQL_LINT_PATH"];
    }
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

// A shebang script is not directly spawnable on Windows; CI is ubuntu.
const describeOnPosix = process.platform === "win32" ? describe.skip : describe;

describeOnPosix("dsql-lint JSON contract", () => {
  test("rejects output that is not JSON", () => {
    // What a native crash looks like: a panic on stdout instead of JSON.
    withFakeDsqlLint("thread 'main' panicked at 'index out of bounds'", () => {
      expect(() => transformMigration("SELECT 1;")).toThrow(
        /dsql-lint did not produce valid JSON/,
      );
    });
  });

  test("rejects an unsupported schema_version rather than misreading the shape", () => {
    withFakeDsqlLint(JSON.stringify({ schema_version: 2, files: [] }), () => {
      expect(() => transformMigration("SELECT 1;")).toThrow(
        /schema_version 2 is not supported/,
      );
    });
  });
});

describe("Migration Transformer (dsql-lint)", () => {
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

  describe("CREATE INDEX transformation", () => {
    test("converts CREATE INDEX to CREATE INDEX ASYNC", () => {
      const input = `CREATE INDEX "user_email_idx" ON "user"("email");`;

      const result = transformMigration(input);

      // dsql-lint >= 0.2 classifies the ASYNC rewrite as fixed_with_warning
      // (exit 3): the index builds in the background and isn't ready when the
      // statement returns. The rewrite still happens.
      expect(result.exitCode).toBe(3);
      expect(result.sql).toContain("CREATE INDEX ASYNC");
      expect(result.sql).not.toMatch(/CREATE\s+INDEX\s+"/);
    });

    test("does not double-convert already ASYNC indexes", () => {
      const input = `CREATE INDEX ASYNC "user_email_idx" ON "user"("email");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).not.toContain("ASYNC ASYNC");
      expect(result.sql).toContain("CREATE INDEX ASYNC");
    });
  });

  describe("foreign key removal", () => {
    test("removes ALTER TABLE ADD FOREIGN KEY statements", () => {
      const input = `ALTER TABLE "post" ADD CONSTRAINT "post_authorId_fkey" FOREIGN KEY ("authorId") REFERENCES "user"("id");`;

      const result = transformMigration(input);

      // FK removal is FixedWithWarning → exit 3.
      expect(result.exitCode).toBe(3);
      expect(result.sql).not.toContain("FOREIGN KEY");
      expect(result.sql).not.toContain("REFERENCES");
    });

    test("DROP CONSTRAINT for foreign keys is unfixable", () => {
      const input = `ALTER TABLE "Pet" DROP CONSTRAINT "Pet_ownerId_fkey";`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(1);
      expect(hasDiagnosticWithStatus(result.output, "unfixable")).toBe(true);
      expect(result.sql).toContain("DROP CONSTRAINT");
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
    });
  });
});

describe("worseExitCode", () => {
  test("unfixable (1) beats everything", () => {
    expect(worseExitCode(0, 1)).toBe(1);
    expect(worseExitCode(3, 1)).toBe(1);
    expect(worseExitCode(1, 3)).toBe(1);
  });

  test("warning (3) beats clean (0)", () => {
    expect(worseExitCode(0, 3)).toBe(3);
    expect(worseExitCode(3, 0)).toBe(3);
  });

  test("clean stays clean", () => {
    expect(worseExitCode(0, 0)).toBe(0);
  });
});

describe("transformMigrationFile (Drizzle statement-breakpoint)", () => {
  const BREAKPOINT = "--> statement-breakpoint";

  test("transforms each statement and preserves breakpoints", () => {
    const input = [
      `CREATE TABLE "owner" ("id" UUID PRIMARY KEY);`,
      `CREATE INDEX "pet_idx" ON "pet"("ownerId");`,
    ].join(`\n${BREAKPOINT}\n`);

    const result = transformMigrationFile(input);

    // CREATE INDEX → ASYNC is fixed_with_warning (exit 3) in dsql-lint >= 0.2.
    expect(result.exitCode).toBe(3);
    expect(result.sql).toContain('CREATE TABLE "owner"');
    expect(result.sql).toContain("CREATE INDEX ASYNC");
    expect(result.sql).toContain(BREAKPOINT);
    // Two statements → exactly one breakpoint between them.
    expect(result.sql.split(BREAKPOINT)).toHaveLength(2);
  });

  test("drops removed statements (foreign keys) and reports exit 3", () => {
    const input = [
      `CREATE TABLE "pet" ("id" UUID PRIMARY KEY);`,
      `ALTER TABLE "pet" ADD CONSTRAINT "pet_fk" FOREIGN KEY ("ownerId") REFERENCES "owner"("id");`,
    ].join(`\n${BREAKPOINT}\n`);

    const result = transformMigrationFile(input);

    expect(result.exitCode).toBe(3);
    expect(result.sql).toContain('CREATE TABLE "pet"');
    expect(result.sql).not.toContain("FOREIGN KEY");
    // Only the surviving statement remains — no dangling breakpoint.
    expect(result.sql).not.toContain(BREAKPOINT);
  });

  test("single-statement input (no breakpoints) still transforms", () => {
    const result = transformMigrationFile(`CREATE INDEX "idx" ON "t"("c");`);

    // Single CREATE INDEX → ASYNC: fixed_with_warning (exit 3), see above.
    expect(result.exitCode).toBe(3);
    expect(result.sql).toContain("CREATE INDEX ASYNC");
    expect(result.outputs).toHaveLength(1);
  });

  test("rejects a breakpoint-free file with multiple statements", () => {
    // Drizzle Kit `breakpoints: false` produces this shape; the migrator would
    // otherwise send both DDLs in one execute() and DSQL would reject it.
    const input = [
      `CREATE TABLE "a" ("id" UUID PRIMARY KEY);`,
      `CREATE TABLE "b" ("id" UUID PRIMARY KEY);`,
    ].join("\n");

    expect(() => transformMigrationFile(input)).toThrow(
      /multiple SQL statements/,
    );
  });

  test("does not reject a single statement with a semicolon inside a string", () => {
    // A lone statement whose only semicolon lives in a string literal must not
    // be mistaken for a multi-statement file.
    const result = transformMigrationFile(
      `CREATE TABLE "t" ("note" TEXT DEFAULT 'a;b');`,
    );

    expect(result.sql).toContain('CREATE TABLE "t"');
    expect(result.outputs).toHaveLength(1);
  });
});
