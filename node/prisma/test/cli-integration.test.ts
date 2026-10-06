/**
 * CLI Integration Tests
 *
 * These tests run the actual CLI commands to verify the golden path
 * workflow works end-to-end with dsql-lint.
 */
import { execSync, spawnSync } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { transactionBlocks } from "./transactions";

function execAllowAdvisories(command: string): string {
  try {
    return execSync(command, {
      cwd: path.join(__dirname, ".."),
      encoding: "utf-8",
    });
  } catch (error: unknown) {
    const execError = error as { stdout?: string; status?: number };
    if (execError.status === 3) {
      return execError.stdout ?? "";
    }
    throw error;
  }
}

describe("CLI Integration", () => {
  let tempDir: string;

  beforeAll(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "prisma-cli-test-"));
  });

  afterAll(() => {
    fs.rmSync(tempDir, { recursive: true });
  });

  describe("README golden path workflow", () => {
    test("transform from file works", () => {
      const migration = `CREATE TABLE "user" ("id" UUID PRIMARY KEY);
CREATE INDEX "user_idx" ON "user"("id");`;
      const inputPath = path.join(tempDir, "input.sql");
      const outputPath = path.join(tempDir, "output.sql");
      fs.writeFileSync(inputPath, migration);

      execAllowAdvisories(
        `npm run dsql-transform ${inputPath} -- -o ${outputPath}`,
      );

      const output = fs.readFileSync(outputPath, "utf-8");
      expect(output).toContain("CREATE INDEX ASYNC");
    });

    test("transform from stdin works", () => {
      const migration = `CREATE TABLE "user" ("id" UUID PRIMARY KEY);
CREATE INDEX "user_idx" ON "user"("id");`;
      const inputPath = path.join(tempDir, "stdin-input.sql");
      fs.writeFileSync(inputPath, migration);

      const output = execAllowAdvisories(
        `cat ${inputPath} | npm run dsql-transform 2>/dev/null`,
      );

      expect(output).toContain("CREATE INDEX ASYNC");
    });

    test("transform from stdin splits statements into transactions", () => {
      const migration = `CREATE TABLE "user" ("id" UUID PRIMARY KEY);
CREATE TABLE "post" ("id" UUID PRIMARY KEY);`;
      const inputPath = path.join(tempDir, "stdin-split.sql");
      fs.writeFileSync(inputPath, migration);

      const output = execAllowAdvisories(
        `cat ${inputPath} | npm run --silent dsql-transform 2>/dev/null`,
      );

      expect(transactionBlocks(output)).toHaveLength(2);
    });

    test("drains a large split migration to a slow stdout reader before exiting 3", () => {
      const statements = Array.from(
        { length: 1500 },
        (_, i) => `CREATE TABLE "table_${i}" ("id" UUID PRIMARY KEY);`,
      );
      const inputPath = path.join(tempDir, "slow-reader.sql");
      fs.writeFileSync(inputPath, statements.join("\n"));
      const expected =
        statements.map((sql) => `BEGIN;\n\n${sql}\n\nCOMMIT;`).join("\n\n") +
        "\n";
      expect(Buffer.byteLength(expected)).toBeGreaterThan(64 * 1024);

      const result = spawnSync(
        "bash",
        [
          "-o",
          "pipefail",
          "-c",
          '"$1" "$2" transform "$3" | (sleep 1; cat)',
          "--",
          process.execPath,
          path.join(__dirname, "../dist/cli/index.js"),
          inputPath,
        ],
        { encoding: "utf-8" },
      );

      expect(result.error).toBeUndefined();
      expect(result.status).toBe(3);
      expect(result.stdout).toBe(expected);
    });

    test.each([2, 101])(
      "does not write output after dsql-lint exits %i",
      (exitCode) => {
        // Exercise the CLI's unexpected-exit boundary with a complete lint
        // response; real lint errors do not normally include writable SQL.
        const lintPath = path.join(tempDir, `lint-exit-${exitCode}`);
        fs.writeFileSync(
          lintPath,
          `#!${process.execPath}
const fs = require("fs");
const sql = fs.readFileSync(0, "utf-8");
console.log(JSON.stringify({
  schema_version: 1,
  files: [{ file: "<stdin>", diagnostics: [], error: null, output_file: null, fixed_sql: sql }],
  summary: { errors: 0, warnings: 0, fixed: 0 }
}));
process.exitCode = ${exitCode};
`,
          { mode: 0o755 },
        );
        const inputPath = path.join(tempDir, "fatal-input.sql");
        fs.writeFileSync(inputPath, 'CREATE TABLE "a" ("id" UUID);');

        for (const command of ["transform", "migrate"]) {
          const outputPath = path.join(
            tempDir,
            `fatal-${command}-${exitCode}.sql`,
          );
          const result = spawnSync(
            process.execPath,
            [
              path.join(__dirname, "../dist/cli/index.js"),
              command,
              command === "transform"
                ? inputPath
                : "prisma/veterinary-schema.prisma",
              "-o",
              outputPath,
            ],
            {
              cwd: path.join(__dirname, ".."),
              encoding: "utf-8",
              env: { ...process.env, DSQL_LINT_PATH: lintPath },
            },
          );

          expect(result.error).toBeUndefined();
          expect(result.status).toBe(exitCode);
          expect(fs.existsSync(outputPath)).toBe(false);
          expect(result.stdout).not.toContain("Migration written to");
        }
      },
    );

    test("prints skipped-splitting advisories on stderr while writing SQL to stdout", () => {
      const inputPath = path.join(tempDir, "skipped.sql");
      const sql = `SET LOCAL search_path TO "public";
CREATE TABLE "a" ("id" UUID PRIMARY KEY);
CREATE TABLE "b" ("id" UUID PRIMARY KEY);`;
      fs.writeFileSync(inputPath, sql);

      const result = spawnSync(
        process.execPath,
        [path.join(__dirname, "../dist/cli/index.js"), "transform", inputPath],
        { encoding: "utf-8" },
      );

      expect(result.error).toBeUndefined();
      expect(result.status).toBe(3);
      expect(result.stdout.replace(/\s+/g, " ").trim()).toBe(
        sql.replace(/\s+/g, " ").trim(),
      );
      expect(result.stderr).toMatch(/WARNING.*splitting.*skipped.*SET LOCAL/i);
      expect(result.stderr).toMatch(/each DDL statement.*transaction/i);
    });

    test("migrate reports skipped splitting but exits 0 after writing the migration", () => {
      // Prisma normally generates no transaction-scoped settings. Substitute
      // only its diff subprocess to exercise migrate's advisory handling.
      const binDir = path.join(tempDir, "prisma-diff-bin");
      fs.mkdirSync(binDir);
      const sql = `SET LOCAL search_path TO "public";
CREATE TABLE "a" ("id" UUID PRIMARY KEY);
CREATE TABLE "b" ("id" UUID PRIMARY KEY);`;
      fs.writeFileSync(
        path.join(binDir, "npx"),
        `#!${process.execPath}
const args = process.argv.slice(2);
if (JSON.stringify(args) !== JSON.stringify([
  "prisma", "migrate", "diff", "--from-empty", "--to-schema", "prisma/veterinary-schema.prisma", "--script"
])) process.exit(2);
process.stdout.write(${JSON.stringify(sql)});
`,
        { mode: 0o755 },
      );
      const outputPath = path.join(tempDir, "skipped-migrate.sql");
      const result = spawnSync(
        process.execPath,
        [
          path.join(__dirname, "../dist/cli/index.js"),
          "migrate",
          "prisma/veterinary-schema.prisma",
          "-o",
          outputPath,
        ],
        {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
          env: {
            ...process.env,
            PATH: `${binDir}${path.delimiter}${process.env.PATH}`,
          },
        },
      );

      expect(result.error).toBeUndefined();
      expect(result.status).toBe(0);
      expect(result.stderr).toMatch(/WARNING.*splitting.*skipped.*SET LOCAL/i);
      expect(result.stdout).toContain("Migration written to");
      expect(
        fs.readFileSync(outputPath, "utf-8").replace(/\s+/g, " ").trim(),
      ).toBe(sql.replace(/\s+/g, " ").trim());
    });

    test("validator exits nonzero for unfixable SQL", () => {
      const schema = `
datasource db {
  provider = "postgresql"
}

model User {
  id   String   @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  tags String[]
}
`;
      const schemaPath = path.join(tempDir, "invalid.prisma");
      fs.writeFileSync(schemaPath, schema);

      try {
        execSync(`npm run validate ${schemaPath}`, {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
          stdio: "pipe",
        });
        fail("Expected validator to fail");
      } catch (error: unknown) {
        const execError = error as { stdout?: string; status?: number };
        expect(execError.stdout?.toLowerCase()).toContain("array");
        expect(execError.status).toBe(1);
      }
    });

    test("validator passes valid schema", () => {
      const validSchema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  id   String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  name String
}
`;
      const schemaPath = path.join(tempDir, "valid.prisma");
      fs.writeFileSync(schemaPath, validSchema);

      const output = execSync(`npm run validate ${schemaPath}`, {
        cwd: path.join(__dirname, ".."),
        encoding: "utf-8",
      });

      expect(output).toContain("DSQL-compatible");
    });

    test("dsql-migrate command works end-to-end", () => {
      const outputPath = path.join(tempDir, "migration.sql");

      const result = execAllowAdvisories(
        `npm run dsql-migrate -- prisma/veterinary-schema.prisma -o ${outputPath}`,
      );

      expect(result).toContain("Validating");
      expect(result).toContain("Generating migration");
      expect(result).toContain("Transforming");
      expect(result).toContain("Migration written to");

      const output = fs.readFileSync(outputPath, "utf-8");
      expect(output).toContain("CREATE INDEX ASYNC");
      expect(output).toContain("FOREIGN KEY");
      expect(output).toContain("NOT VALID");
    });

    test("dsql-migrate puts each statement in its own transaction", () => {
      const outputPath = path.join(tempDir, "migration-split.sql");

      execAllowAdvisories(
        `npm run dsql-migrate -- prisma/veterinary-schema.prisma -o ${outputPath}`,
      );

      const output = fs.readFileSync(outputPath, "utf-8");
      // Veterinary schema: CREATE SCHEMA, 5 tables, 2 indexes, 3 foreign keys.
      expect(transactionBlocks(output)).toHaveLength(11);
    });

    test("dsql-migrate rewrites generated SERIAL columns", () => {
      const serialSchema = `
datasource db {
  provider = "postgresql"
}

model User {
  id   Int    @id @default(autoincrement())
  name String
}
`;
      const schemaPath = path.join(tempDir, "serial-migrate.prisma");
      const outputPath = path.join(tempDir, "serial-migration.sql");
      fs.writeFileSync(schemaPath, serialSchema);

      execAllowAdvisories(
        `npm run dsql-migrate -- ${schemaPath} -o ${outputPath}`,
      );

      const output = fs.readFileSync(outputPath, "utf-8");
      expect(output).toContain("GENERATED BY DEFAULT AS IDENTITY");
      expect(output).not.toContain("SERIAL");
    });

    test("lint command detects issues", () => {
      const migration = `CREATE INDEX "idx" ON "t"("col");`;
      const inputPath = path.join(tempDir, "lint-input.sql");
      fs.writeFileSync(inputPath, migration);

      try {
        execSync(`npm run dsql-lint ${inputPath}`, {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
          stdio: "pipe",
        });
        fail("Expected lint to fail");
      } catch (error: unknown) {
        const execError = error as { stderr?: string; status?: number };
        expect(execError.stderr).toContain("ASYNC");
        expect(execError.status).toBe(1);
      }
    });

    test("lint command passes clean SQL", () => {
      const migration = `CREATE TABLE "user" ("id" UUID PRIMARY KEY);`;
      const inputPath = path.join(tempDir, "lint-clean.sql");
      fs.writeFileSync(inputPath, migration);

      execSync(`npm run dsql-lint ${inputPath}`, {
        cwd: path.join(__dirname, ".."),
        encoding: "utf-8",
      });
    });

    test("transform preserves DROP CONSTRAINT for a foreign key", () => {
      const migration = `ALTER TABLE "child" DROP CONSTRAINT "child_parent_fkey";`;
      const inputPath = path.join(tempDir, "unfixable.sql");
      const outputPath = path.join(tempDir, "unfixable-out.sql");
      fs.writeFileSync(inputPath, migration);

      execSync(`npm run dsql-transform ${inputPath} -- -o ${outputPath}`, {
        cwd: path.join(__dirname, ".."),
        encoding: "utf-8",
        stdio: "pipe",
      });

      expect(fs.readFileSync(outputPath, "utf-8")).toContain("DROP CONSTRAINT");
    });

    test("transform marks ALTER-based FK migrations NOT VALID", () => {
      const migration = `CREATE TABLE "post" (
    "id" UUID NOT NULL,
    "authorId" UUID NOT NULL,
    PRIMARY KEY ("id")
);
ALTER TABLE "post" ADD CONSTRAINT "post_authorId_fkey" FOREIGN KEY ("authorId") REFERENCES "user"("id");
CREATE INDEX "post_authorId_idx" ON "post"("authorId");`;
      const inputPath = path.join(tempDir, "fixable.sql");
      const outputPath = path.join(tempDir, "fixable-out.sql");
      fs.writeFileSync(inputPath, migration);

      let thrown: { status?: number } | undefined;
      try {
        execSync(`npm run dsql-transform ${inputPath} -- -o ${outputPath}`, {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
        });
      } catch (e) {
        thrown = e as { status?: number };
      }
      expect(thrown?.status).toBe(3);
      const output = fs.readFileSync(outputPath, "utf-8");
      expect(output).toContain("FOREIGN KEY");
      expect(output).toContain("NOT VALID");
    });

    test("validate rejects unknown flags", () => {
      try {
        execSync(`npm run validate -- --unknown-flag`, {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
          stdio: "pipe",
        });
        fail("Expected CLI to fail on unknown flag");
      } catch (error: unknown) {
        const execError = error as { stderr?: string; status?: number };
        expect(execError.stderr).toContain("Unknown flag: --unknown-flag");
        expect(execError.status).toBe(1);
      }
    });

    test("migrate rejects unknown flags", () => {
      try {
        execSync(`npm run dsql-migrate -- schema.prisma -o out.sql --bogus`, {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
          stdio: "pipe",
        });
        fail("Expected CLI to fail on unknown flag");
      } catch (error: unknown) {
        const execError = error as { stderr?: string; status?: number };
        expect(execError.stderr).toContain("Unknown flag: --bogus");
        expect(execError.status).toBe(1);
      }
    });

    test("transform rejects unknown flags", () => {
      try {
        execSync(`npm run dsql-transform -- --verbose`, {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
          stdio: "pipe",
        });
        fail("Expected CLI to fail on unknown flag");
      } catch (error: unknown) {
        const execError = error as { stderr?: string; status?: number };
        expect(execError.stderr).toContain("Unknown flag: --verbose");
        expect(execError.status).toBe(1);
      }
    });

    test("lint rejects unknown flags", () => {
      try {
        execSync(`npm run dsql-lint -- --fix`, {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
          stdio: "pipe",
        });
        fail("Expected CLI to fail on unknown flag");
      } catch (error: unknown) {
        const execError = error as { stderr?: string; status?: number };
        expect(execError.stderr).toContain("Unknown flag: --fix");
        expect(execError.status).toBe(1);
      }
    });

    test("prisma migrate diff piped to dsql-transform produces valid output", () => {
      const output = execAllowAdvisories(
        "npx prisma migrate diff --from-empty --to-schema prisma/veterinary-schema.prisma --script | npm run dsql-transform 2>/dev/null",
      );

      expect(output).toContain("CREATE INDEX ASYNC");
      expect(output).toContain("FOREIGN KEY");
      expect(output).toContain("NOT VALID");
      expect(output).toMatch(/REFERENCES.*ON DELETE/);
      expect(output).toContain('CREATE TABLE "owner"');
      expect(output).toContain('CREATE TABLE "pet"');
    });
  });
});
