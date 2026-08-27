/**
 * CLI integration tests: run the actual `transform`/`lint` commands end-to-end
 * with dsql-lint to verify the golden-path workflow and exit-code contract.
 * (`generate` needs a drizzle-kit config + schema and is covered by the example
 * app's CI job.)
 */
import { execSync } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

const BREAKPOINT = "--> statement-breakpoint";
const cwd = path.join(__dirname, "..");

// dsql-lint >= 0.2 classifies CREATE INDEX → ASYNC as fixed_with_warning, so
// the CLI exits 3 after still writing the migration. Tolerate exit 3 and return
// whatever the command sent to stdout; re-throw anything else.
function runTransformAllowingWarnings(cmd: string): string {
  try {
    return execSync(cmd, { cwd, encoding: "utf-8" });
  } catch (e) {
    const err = e as { status?: number; stdout?: string };
    if (err.status === 3) {
      return err.stdout ?? "";
    }
    throw e;
  }
}

describe("CLI Integration", () => {
  let tempDir: string;

  beforeAll(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "drizzle-cli-test-"));
  });

  afterAll(() => {
    fs.rmSync(tempDir, { recursive: true });
  });

  test("transform from file rewrites CREATE INDEX for DSQL", () => {
    const inputPath = path.join(tempDir, "input.sql");
    const outputPath = path.join(tempDir, "output.sql");
    fs.writeFileSync(inputPath, `CREATE INDEX "user_idx" ON "user"("id");`);

    runTransformAllowingWarnings(
      `npm run dsql-transform ${inputPath} -- -o ${outputPath}`,
    );

    expect(fs.readFileSync(outputPath, "utf-8")).toContain(
      "CREATE INDEX ASYNC",
    );
  });

  test("transform from stdin works", () => {
    const inputPath = path.join(tempDir, "stdin-input.sql");
    fs.writeFileSync(inputPath, `CREATE INDEX "user_idx" ON "user"("id");`);

    const output = runTransformAllowingWarnings(
      `cat ${inputPath} | npm run dsql-transform 2>/dev/null`,
    );

    expect(output).toContain("CREATE INDEX ASYNC");
  });

  test("transform preserves Drizzle statement-breakpoints", () => {
    const inputPath = path.join(tempDir, "bp-input.sql");
    const outputPath = path.join(tempDir, "bp-output.sql");
    fs.writeFileSync(
      inputPath,
      [
        `CREATE TABLE "user" ("id" UUID PRIMARY KEY);`,
        `CREATE INDEX "user_idx" ON "user"("id");`,
      ].join(`\n${BREAKPOINT}\n`),
    );

    runTransformAllowingWarnings(
      `npm run dsql-transform ${inputPath} -- -o ${outputPath}`,
    );

    const output = fs.readFileSync(outputPath, "utf-8");
    expect(output).toContain("CREATE INDEX ASYNC");
    expect(output).toContain(BREAKPOINT);
  });

  test("rejects a breakpoint-free file with multiple statements", () => {
    // Drizzle Kit `breakpoints: false` yields multiple DDLs with no marker,
    // which the migrator can't run one-per-statement. The CLI must reject it.
    const inputPath = path.join(tempDir, "multi.sql");
    fs.writeFileSync(
      inputPath,
      `CREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY);`,
    );

    let execError: { stderr?: string; status?: number } | undefined;
    try {
      execSync(`npm run dsql-transform ${inputPath}`, {
        cwd,
        encoding: "utf-8",
        stdio: "pipe",
      });
    } catch (error: unknown) {
      execError = error as { stderr?: string; status?: number };
    }
    expect(execError).toBeDefined();
    expect(execError?.stderr).toContain("multiple SQL statements");
    expect(execError?.status).toBe(1);
  });

  test("transform marks foreign keys NOT VALID and exits 3", () => {
    const inputPath = path.join(tempDir, "fk-input.sql");
    const outputPath = path.join(tempDir, "fk-output.sql");
    fs.writeFileSync(
      inputPath,
      [
        `CREATE TABLE "post" ("id" UUID NOT NULL, "authorId" UUID NOT NULL, PRIMARY KEY ("id"));`,
        `ALTER TABLE "post" ADD CONSTRAINT "post_authorId_fkey" FOREIGN KEY ("authorId") REFERENCES "user"("id");`,
      ].join(`\n${BREAKPOINT}\n`),
    );

    let thrown: { status?: number } | undefined;
    try {
      execSync(`npm run dsql-transform ${inputPath} -- -o ${outputPath}`, {
        cwd,
        encoding: "utf-8",
      });
    } catch (e) {
      thrown = e as { status?: number };
    }
    expect(thrown?.status).toBe(3);

    const output = fs.readFileSync(outputPath, "utf-8");
    expect(output).toContain('CREATE TABLE "post"');
    expect(output).toContain("FOREIGN KEY");
    expect(output).toContain("NOT VALID");
  });

  test("transform reports unfixable statements with a non-zero exit", () => {
    const inputPath = path.join(tempDir, "unfixable.sql");
    fs.writeFileSync(
      inputPath,
      `ALTER TABLE "t" ADD CONSTRAINT "t_pkey" PRIMARY KEY ("id");`,
    );

    let execError: { stderr?: string; status?: number } | undefined;
    try {
      execSync(`npm run dsql-transform ${inputPath}`, {
        cwd,
        encoding: "utf-8",
        stdio: "pipe",
      });
    } catch (error: unknown) {
      execError = error as { stderr?: string; status?: number };
    }
    expect(execError).toBeDefined();
    expect(execError?.stderr).toContain("ERROR —");
    expect(execError?.status).toBe(1);
  });

  test("lint detects issues with exit 1", () => {
    const inputPath = path.join(tempDir, "lint-input.sql");
    fs.writeFileSync(inputPath, `CREATE INDEX "idx" ON "t"("col");`);

    let execError: { stderr?: string; status?: number } | undefined;
    try {
      execSync(`npm run dsql-lint ${inputPath}`, {
        cwd,
        encoding: "utf-8",
        stdio: "pipe",
      });
    } catch (error: unknown) {
      execError = error as { stderr?: string; status?: number };
    }
    expect(execError).toBeDefined();
    expect(execError?.stderr).toContain("ASYNC");
    expect(execError?.status).toBe(1);
  });

  test("lint passes clean SQL", () => {
    const inputPath = path.join(tempDir, "lint-clean.sql");
    fs.writeFileSync(inputPath, `CREATE TABLE "user" ("id" UUID PRIMARY KEY);`);

    execSync(`npm run dsql-lint ${inputPath}`, { cwd, encoding: "utf-8" });
  });

  test("transform -o without a value is rejected", () => {
    let execError: { stderr?: string; status?: number } | undefined;
    try {
      execSync(`npm run dsql-transform -- -o`, {
        cwd,
        encoding: "utf-8",
        stdio: "pipe",
      });
    } catch (error: unknown) {
      execError = error as { stderr?: string; status?: number };
    }
    expect(execError).toBeDefined();
    expect(execError?.stderr).toContain("-o/--output requires a file argument");
    expect(execError?.status).toBe(1);
  });

  test("transform rejects unknown flags", () => {
    let execError: { stderr?: string; status?: number } | undefined;
    try {
      execSync(`npm run dsql-transform -- --verbose`, {
        cwd,
        encoding: "utf-8",
        stdio: "pipe",
      });
    } catch (error: unknown) {
      execError = error as { stderr?: string; status?: number };
    }
    expect(execError).toBeDefined();
    expect(execError?.stderr).toContain("Unknown flag: --verbose");
    expect(execError?.status).toBe(1);
  });

  test("lint rejects unknown flags", () => {
    let execError: { stderr?: string; status?: number } | undefined;
    try {
      execSync(`npm run dsql-lint -- --fix`, {
        cwd,
        encoding: "utf-8",
        stdio: "pipe",
      });
    } catch (error: unknown) {
      execError = error as { stderr?: string; status?: number };
    }
    expect(execError).toBeDefined();
    expect(execError?.stderr).toContain("Unknown flag: --fix");
    expect(execError?.status).toBe(1);
  });
});

/**
 * Argument-parsing contract. These drive the CLI directly (rather than through
 * the npm scripts) so command dispatch and the `--` separator are exercised the
 * way a user invokes the published bin.
 */
describe("CLI argument parsing", () => {
  const CLI = "npx tsx src/cli/index.ts";

  /** Run the CLI expecting failure; returns the captured stderr and status. */
  function runExpectingFailure(args: string): {
    stderr: string;
    status: number | undefined;
  } {
    try {
      execSync(`${CLI} ${args}`, { cwd, encoding: "utf-8", stdio: "pipe" });
    } catch (error: unknown) {
      const execError = error as { stderr?: string; status?: number };
      return { stderr: execError.stderr ?? "", status: execError.status };
    }
    // The catch returns, so reaching here means the command succeeded when the
    // caller required a failure.
    throw new Error(`Expected \`${args}\` to exit non-zero`);
  }

  test("no arguments prints help and exits 0", () => {
    const out = execSync(CLI, { cwd, encoding: "utf-8" });
    expect(out).toContain("Aurora DSQL Drizzle Tools");
    expect(out).toContain("generate");
  });

  test.each(["--help", "-h"])("%s prints help and exits 0", (flag) => {
    const out = execSync(`${CLI} ${flag}`, { cwd, encoding: "utf-8" });
    expect(out).toContain("Usage:");
  });

  test("an unknown command exits 1 and names the command", () => {
    const { stderr, status } = runExpectingFailure("migrate");
    expect(stderr).toContain("Unknown command: migrate");
    expect(status).toBe(1);
  });

  test.each(["generate", "transform", "lint"])(
    "%s --help exits 0",
    (command) => {
      const out = execSync(`${CLI} ${command} --help`, {
        cwd,
        encoding: "utf-8",
      });
      expect(out).toContain("Usage:");
    },
  );

  test("generate flags the recommended workflow in its help", () => {
    const out = execSync(`${CLI} generate --help`, { cwd, encoding: "utf-8" });
    expect(out).toMatch(/drizzle-kit generate/);
    expect(out).toContain("--out");
  });

  test("generate --out without a value is rejected", () => {
    const { stderr, status } = runExpectingFailure("generate --out");
    expect(stderr).toContain("--out requires a directory argument");
    expect(status).toBe(1);
  });

  test("generate --out followed by another flag is rejected", () => {
    // `--out --help` must not silently consume the flag as a directory name.
    const { stderr, status } = runExpectingFailure("generate --out -x");
    expect(stderr).toMatch(/--out requires a directory argument|Unknown flag/);
    expect(status).toBe(1);
  });

  test("generate rejects unknown flags before shelling out to drizzle-kit", () => {
    const { stderr, status } = runExpectingFailure("generate --bogus");
    expect(stderr).toContain("Unknown flag: --bogus");
    expect(stderr).not.toContain("drizzle-kit generate failed");
    expect(status).toBe(1);
  });

  test("generate forwards args after `--` to drizzle-kit instead of rejecting them", () => {
    // `--config` is not one of the CLI's own flags, so reaching drizzle-kit at
    // all proves the separator is honoured. drizzle-kit then fails on the
    // missing config, which is the expected outcome here.
    const { stderr, status } = runExpectingFailure(
      "generate -- --config does-not-exist.ts",
    );
    expect(stderr).not.toContain("Unknown flag");
    expect(stderr).toContain("drizzle-kit generate failed");
    expect(status).toBe(1);
  });

  test("lint without an input file is rejected", () => {
    const { stderr, status } = runExpectingFailure("lint");
    expect(stderr).toContain("Input file required");
    expect(status).toBe(1);
  });

  test.each(["transform", "lint"])(
    "%s reports a missing input file",
    (command) => {
      const { stderr, status } = runExpectingFailure(
        `${command} ${path.join(os.tmpdir(), "definitely-not-a-migration.sql")}`,
      );
      expect(stderr).toContain("Input file not found");
      expect(status).toBe(1);
    },
  );
});
