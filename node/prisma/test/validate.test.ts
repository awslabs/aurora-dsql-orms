import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { validateSchema, formatValidationResult } from "../src/cli/validate";

describe("Schema Validator", () => {
  let tempDir: string;

  beforeAll(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "prisma-test-"));
  });

  afterAll(() => {
    fs.rmSync(tempDir, { recursive: true });
  });

  function createTempSchema(content: string): string {
    const schemaPath = path.join(tempDir, `schema-${Date.now()}.prisma`);
    fs.writeFileSync(schemaPath, content);
    return schemaPath;
  }

  describe("relationMode validation", () => {
    test("passes when relationMode = prisma is present", async () => {
      const schema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  id   String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  name String
}
`;
      const result = await validateSchema(createTempSchema(schema));
      const relationModeErrors = result.issues.filter((i) =>
        i.message.includes("relationMode"),
      );
      expect(relationModeErrors).toHaveLength(0);
    });

    test("fails when relationMode is missing", async () => {
      const schema = `
datasource db {
  provider = "postgresql"
}

model User {
  id   String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  name String
}
`;
      const result = await validateSchema(createTempSchema(schema));
      expect(result.valid).toBe(false);
      expect(
        result.issues.some((i) => i.message.includes("relationMode")),
      ).toBe(true);
    });
  });

  describe("dsql-lint SQL validation", () => {
    test("fails when autoincrement() is used (SERIAL in SQL)", async () => {
      const schema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  id   Int    @id @default(autoincrement())
  name String
}
`;
      const result = await validateSchema(createTempSchema(schema));
      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.message.includes("SERIAL"))).toBe(
        true,
      );
    });

    test("reports CREATE INDEX without ASYNC", async () => {
      const schema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  id   String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  name String @db.VarChar(100)

  @@index([name])
}
`;
      const result = await validateSchema(createTempSchema(schema));
      expect(result.valid).toBe(false);
      expect(
        result.issues.some((i) => i.message.includes("CREATE INDEX")),
      ).toBe(true);
    });

    test("fails when @db.Serial is used", async () => {
      const schema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  id   Int    @id @db.Serial
  name String
}
`;
      const result = await validateSchema(createTempSchema(schema));
      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.message.includes("Serial"))).toBe(
        true,
      );
    });

    test("fails when @db.SmallSerial is used", async () => {
      const schema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  id   Int    @id @db.SmallSerial
  name String
}
`;
      const result = await validateSchema(createTempSchema(schema));
      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.message.includes("SmallSerial"))).toBe(
        true,
      );
    });

    test("fails when @db.BigSerial is used", async () => {
      const schema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  id   BigInt @id @db.BigSerial
  name String
}
`;
      const result = await validateSchema(createTempSchema(schema));
      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.message.includes("BigSerial"))).toBe(
        true,
      );
    });

    test("fails when @@fulltext is used", async () => {
      const schema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  id   String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  name String

  @@fulltext([name])
}
`;
      const result = await validateSchema(createTempSchema(schema));
      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.message.includes("fulltext"))).toBe(
        true,
      );
    });
  });

  describe("valid schema", () => {
    test("passes for DSQL-compatible schema", async () => {
      const schema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  id    String  @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  name  String  @db.VarChar(100)
  email String? @db.VarChar(255)
}
`;
      const result = await validateSchema(createTempSchema(schema));
      expect(result.valid).toBe(true);
      expect(result.issues).toHaveLength(0);
    });
  });

  describe("formatValidationResult", () => {
    test("formats success message", async () => {
      const result = { valid: true, issues: [] };
      const output = formatValidationResult(result, "schema.prisma");
      expect(output).toContain("✓");
      expect(output).toContain("DSQL-compatible");
    });

    test("formats error messages with line numbers", async () => {
      const result = {
        valid: false,
        issues: [
          {
            message: "Test error",
            line: 10,
            suggestion: "Fix it",
          },
        ],
      };
      const output = formatValidationResult(result, "schema.prisma");
      expect(output).toContain("✗");
      expect(output).toContain("line 10");
      expect(output).toContain("Fix it");
    });
  });

  describe("file handling", () => {
    test("returns error for non-existent file", async () => {
      const result = await validateSchema("/nonexistent/schema.prisma");
      expect(result.valid).toBe(false);
      expect(result.issues[0]?.message).toContain("not found");
    });

    test("returns error when prisma cannot parse schema", async () => {
      const schema = `
datasource db {
  provider     = "postgresql"
  relationMode = "prisma"
}

model User {
  this is not valid prisma syntax
}
`;
      const result = await validateSchema(createTempSchema(schema));
      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.message.includes("error"))).toBe(true);
    });
  });
});
