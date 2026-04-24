import { transformMigration, lintMigration } from "../src/cli/transform";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

describe("dsql-lint binary resolution", () => {
  test("throws helpful error when dsql-lint is not found", () => {
    const originalPath = process.env["DSQL_LINT_PATH"];
    const originalPATH = process.env["PATH"];
    try {
      process.env["DSQL_LINT_PATH"] = "";
      delete process.env["DSQL_LINT_PATH"];
      process.env["PATH"] = "/nonexistent";

      expect(() => transformMigration("SELECT 1;")).toThrow(
        /dsql-lint not found/,
      );
    } finally {
      if (originalPath !== undefined) {
        process.env["DSQL_LINT_PATH"] = originalPath;
      }
      process.env["PATH"] = originalPATH;
    }
  });

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

      expect(result.exitCode).toBe(0);
      expect(result.sql).toContain('CREATE TABLE "user"');
      expect(result.sql).toContain('CREATE TABLE "post"');
    });
  });

  describe("CREATE INDEX transformation", () => {
    test("converts CREATE INDEX to CREATE INDEX ASYNC", () => {
      const input = `CREATE INDEX "user_email_idx" ON "user"("email");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).toContain("CREATE INDEX ASYNC");
    });

    test("converts CREATE UNIQUE INDEX to CREATE UNIQUE INDEX ASYNC", () => {
      const input = `CREATE UNIQUE INDEX "user_email_key" ON "user"("email");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).toContain("UNIQUE INDEX ASYNC");
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

      expect(result.exitCode).toBe(0);
      expect((result.sql.match(/INDEX\s+ASYNC/g) || []).length).toBe(3);
    });
  });

  describe("foreign key removal", () => {
    test("removes ALTER TABLE ADD FOREIGN KEY statements", () => {
      const input = `CREATE TABLE "post" (
    "id" UUID NOT NULL,
    "authorId" UUID NOT NULL,
    PRIMARY KEY ("id")
);

ALTER TABLE "post" ADD CONSTRAINT "post_authorId_fkey" FOREIGN KEY ("authorId") REFERENCES "user"("id");`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).not.toContain("FOREIGN KEY");
      expect(result.sql).not.toContain("REFERENCES");
      expect(result.sql).toContain('CREATE TABLE "post"');
    });

    test("removes inline REFERENCES from CREATE TABLE", () => {
      const input = `CREATE TABLE "post" (
    "id" UUID NOT NULL,
    "authorId" UUID REFERENCES "user"("id"),
    PRIMARY KEY ("id")
);`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(0);
      expect(result.sql).not.toContain("REFERENCES");
      expect(result.sql).toContain('CREATE TABLE "post"');
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

      expect(result.exitCode).toBe(0);
      expect(result.sql).toContain("CREATE INDEX ASYNC");
      expect(result.sql).not.toContain("FOREIGN KEY");
      expect(result.sql).toContain('CREATE TABLE "owner"');
      expect(result.sql).toContain('CREATE TABLE "pet"');
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
      expect(result.sql).toContain("email");
    });

    test("returns exit code 1 for unfixable errors", () => {
      const input = `ALTER TABLE "t" DROP CONSTRAINT "t_pkey";`;

      const result = transformMigration(input);

      expect(result.exitCode).toBe(1);
      expect(result.stderr).toContain("unfixable");
    });

    test("does not leak temp file paths in stderr", () => {
      const input = `CREATE INDEX "idx" ON "t"("col");`;

      const result = transformMigration(input);

      expect(result.stderr).not.toMatch(/\/tmp\//);
      expect(result.stderr).not.toMatch(/\/var\/folders\//);
      expect(result.stderr).not.toContain("dsql-transform-");
    });
  });

  describe("lintMigration", () => {
    let tempDir: string;

    beforeAll(() => {
      tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "lint-test-"));
    });

    afterAll(() => {
      fs.rmSync(tempDir, { recursive: true });
    });

    test("returns exit code 0 for clean SQL", () => {
      const filePath = path.join(tempDir, "clean.sql");
      fs.writeFileSync(filePath, `CREATE TABLE "t" ("id" UUID PRIMARY KEY);`);

      const result = lintMigration(filePath);

      expect(result.exitCode).toBe(0);
    });

    test("returns exit code 1 for SQL with issues", () => {
      const filePath = path.join(tempDir, "issues.sql");
      fs.writeFileSync(filePath, `CREATE INDEX "idx" ON "t"("col");`);

      const result = lintMigration(filePath);

      expect(result.exitCode).toBe(1);
      expect(result.stderr).toContain("ASYNC");
    });
  });
});
