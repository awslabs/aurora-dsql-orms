/**
 * CLI Integration Tests
 *
 * These tests run the actual CLI commands to verify the golden path
 * workflow works end-to-end with dsql-lint.
 */
import { execSync } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

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

      execSync(`npm run dsql-transform ${inputPath} -- -o ${outputPath}`, {
        cwd: path.join(__dirname, ".."),
        encoding: "utf-8",
      });

      const output = fs.readFileSync(outputPath, "utf-8");
      expect(output).toContain("CREATE INDEX ASYNC");
    });

    test("transform from stdin works", () => {
      const migration = `CREATE TABLE "user" ("id" UUID PRIMARY KEY);
CREATE INDEX "user_idx" ON "user"("id");`;
      const inputPath = path.join(tempDir, "stdin-input.sql");
      fs.writeFileSync(inputPath, migration);

      const output = execSync(
        `cat ${inputPath} | npm run dsql-transform 2>/dev/null`,
        {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
        },
      );

      expect(output).toContain("CREATE INDEX ASYNC");
    });

    test("validator catches invalid schema", () => {
      const invalidSchema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  id   Int    @id @default(autoincrement())
  name String
}
`;
      const schemaPath = path.join(tempDir, "invalid.prisma");
      fs.writeFileSync(schemaPath, invalidSchema);

      try {
        execSync(`npm run validate ${schemaPath}`, {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
          stdio: "pipe",
        });
        fail("Expected validator to fail");
      } catch (error: unknown) {
        const execError = error as { stdout?: string; status?: number };
        expect(execError.stdout).toContain("SERIAL");
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

      const result = execSync(
        `npm run dsql-migrate -- prisma/veterinary-schema.prisma -o ${outputPath}`,
        {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
        },
      );

      expect(result).toContain("Validating");
      expect(result).toContain("Generating migration");
      expect(result).toContain("Transforming");
      expect(result).toContain("Migration written to");

      const output = fs.readFileSync(outputPath, "utf-8");
      expect(output).toContain("CREATE INDEX ASYNC");
      expect(output).not.toContain("FOREIGN KEY");
    });

    test("dsql-migrate fails on invalid schema", () => {
      const invalidSchema = `
datasource db {
  provider = "postgresql"
}

model User {
  id   Int    @id @default(autoincrement())
  name String
}
`;
      const schemaPath = path.join(tempDir, "invalid-migrate.prisma");
      const outputPath = path.join(tempDir, "should-not-exist.sql");
      fs.writeFileSync(schemaPath, invalidSchema);

      try {
        execSync(`npm run dsql-migrate -- ${schemaPath} -o ${outputPath}`, {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
          stdio: "pipe",
        });
        fail("Expected dsql-migrate to fail on invalid schema");
      } catch (error: unknown) {
        const execError = error as {
          stdout?: string;
          stderr?: string;
          status?: number;
        };
        const output = (execError.stdout || "") + (execError.stderr || "");
        expect(output).toContain("relationMode");
        expect(output).toContain("Fix the schema errors");
        expect(execError.status).toBe(1);
      }

      expect(fs.existsSync(outputPath)).toBe(false);
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

    test("transform reports unfixable DROP CONSTRAINT with non-zero exit", () => {
      const migration = `ALTER TABLE "t" DROP CONSTRAINT "t_pkey";`;
      const inputPath = path.join(tempDir, "unfixable.sql");
      const outputPath = path.join(tempDir, "unfixable-out.sql");
      fs.writeFileSync(inputPath, migration);

      try {
        execSync(`npm run dsql-transform ${inputPath} -- -o ${outputPath}`, {
          cwd: path.join(__dirname, ".."),
          encoding: "utf-8",
          stdio: "pipe",
        });
        fail("Expected transform to fail");
      } catch (error: unknown) {
        const execError = error as { stderr?: string; status?: number };
        expect(execError.stderr).toContain("unfixable");
        expect(execError.status).toBe(1);
      }
    });

    test("transform fixes FK and index issues with exit code 0", () => {
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

      execSync(`npm run dsql-transform ${inputPath} -- -o ${outputPath}`, {
        cwd: path.join(__dirname, ".."),
        encoding: "utf-8",
      });

      const output = fs.readFileSync(outputPath, "utf-8");
      expect(output).toContain("CREATE INDEX ASYNC");
      expect(output).not.toContain("FOREIGN KEY");
      expect(output).not.toContain("REFERENCES");
      expect(output).toContain('CREATE TABLE "post"');
    });

    test("prisma migrate diff piped to dsql-transform produces valid output", () => {
      const output = execSync(
        "npx prisma migrate diff --from-empty --to-schema prisma/veterinary-schema.prisma --script | npm run dsql-transform 2>/dev/null",
        { cwd: path.join(__dirname, ".."), encoding: "utf-8" },
      );

      expect(output).toContain("CREATE INDEX ASYNC");
      expect(output).not.toContain("FOREIGN KEY");
      expect(output).not.toMatch(/REFERENCES.*ON DELETE/);
      expect(output).toContain('CREATE TABLE "owner"');
      expect(output).toContain('CREATE TABLE "pet"');
    });
  });
});
