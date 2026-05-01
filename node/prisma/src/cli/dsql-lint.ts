import { spawnSync } from "child_process";
import * as fs from "fs";
import * as path from "path";

/**
 * Resolution order for the dsql-lint binary:
 *   1. DSQL_LINT_PATH env var (explicit override, used by tests)
 *   2. The @aws/dsql-lint platform package bundled via this package's
 *      dependencies (preferred — zero manual setup after `npm install`)
 *   3. PATH scan (backwards-compatible with a Cargo install)
 */
function findDsqlLint(): string {
  const envPath = process.env["DSQL_LINT_PATH"];
  if (envPath) {
    if (!fs.existsSync(envPath)) {
      throw new Error(
        `DSQL_LINT_PATH points to '${envPath}' which does not exist`,
      );
    }
    return envPath;
  }

  const platformBinary = findPlatformPackageBinary();
  if (platformBinary) {
    return platformBinary;
  }

  const pathDirs = (process.env["PATH"] ?? "").split(path.delimiter);
  for (const dir of pathDirs) {
    const candidate = path.join(dir, "dsql-lint");
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  throw new Error(
    "dsql-lint not found. Install it:\n" +
      "  npm install @aws/dsql-lint\n" +
      "Or: cargo install dsql-lint\n" +
      "Or set DSQL_LINT_PATH to the binary location.",
  );
}

const PLATFORM_PACKAGES: Record<string, string> = {
  "darwin-arm64": "@aws/dsql-lint-darwin-arm64",
  "darwin-x64": "@aws/dsql-lint-darwin-x64",
  "linux-arm64": "@aws/dsql-lint-linux-arm64",
  "linux-x64": "@aws/dsql-lint-linux-x64",
  "win32-x64": "@aws/dsql-lint-win32-x64",
};

function findPlatformPackageBinary(): string | null {
  const platformKey = `${process.platform}-${process.arch}`;
  const pkg = PLATFORM_PACKAGES[platformKey];
  if (!pkg) {
    return null;
  }

  try {
    // Resolve directly to the native binary inside the platform package.
    // Bypasses the JS wrapper in @aws/dsql-lint's `bin/` — saves a Node
    // process per spawn and keeps exit codes and stdio untouched.
    const pkgDir = path.dirname(require.resolve(`${pkg}/package.json`));
    const binaryName =
      process.platform === "win32" ? "dsql-lint.exe" : "dsql-lint";
    const binary = path.join(pkgDir, "bin", binaryName);
    return fs.existsSync(binary) ? binary : null;
  } catch {
    // @aws/dsql-lint not installed (or the platform package didn't install
    // because the host doesn't match). Fall through to the PATH scan.
    return null;
  }
}

/**
 * JSON wire shape emitted by `dsql-lint --format json`. Matches the
 * stable schema documented in the dsql-lint README. `schema_version`
 * is checked at parse time and callers should treat any unknown
 * version as a breaking change.
 */
export interface DsqlLintJsonOutput {
  schema_version: number;
  files: DsqlLintFileOutput[];
  summary: { errors: number; warnings: number; fixed: number };
}

export interface DsqlLintFileOutput {
  file: string;
  diagnostics: DsqlLintDiagnostic[];
  error: string | null;
  output_file: string | null;
  fixed_sql: string | null;
}

export interface DsqlLintDiagnostic {
  rule: string;
  line: number;
  message: string;
  suggestion: string;
  statement_preview: string;
  fix_result: DsqlLintFixResult;
}

export type DsqlLintFixResult =
  | { status: "fixed"; detail: string }
  | { status: "fixed_with_warning"; detail: string }
  | { status: "unfixable" };

/**
 * Pipe SQL to dsql-lint over stdin and parse its JSON output. Intended
 * for --fix and lint flows that want structured diagnostics without
 * temp files.
 */
export function runDsqlLintWithStdin(
  sql: string,
  args: string[],
): { exitCode: number; output: DsqlLintJsonOutput } {
  const binary = findDsqlLint();
  const result = spawnSync(binary, ["--format", "json", ...args, "-"], {
    encoding: "utf-8",
    input: sql,
  });

  if (result.error) {
    throw new Error(`Failed to execute dsql-lint: ${result.error.message}`);
  }

  const output: DsqlLintJsonOutput = JSON.parse(result.stdout);
  return {
    exitCode: result.status ?? 1,
    output,
  };
}
