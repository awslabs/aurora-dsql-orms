import { spawnSync } from "child_process";
import * as fs from "fs";
import * as path from "path";

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

  const pathDirs = (process.env["PATH"] ?? "").split(path.delimiter);
  for (const dir of pathDirs) {
    const candidate = path.join(dir, "dsql-lint");
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  throw new Error(
    "dsql-lint not found. Install it:\n" +
      "  cargo install dsql-lint\n" +
      "Or set DSQL_LINT_PATH to the binary location.",
  );
}

export interface DsqlLintResult {
  exitCode: number;
  stderr: string;
}

export function runDsqlLint(args: string[]): DsqlLintResult {
  const binary = findDsqlLint();
  const result = spawnSync(binary, args, { encoding: "utf-8" });

  if (result.error) {
    throw new Error(`Failed to execute dsql-lint: ${result.error.message}`);
  }

  return {
    exitCode: result.status ?? 1,
    stderr: result.stderr ?? "",
  };
}
