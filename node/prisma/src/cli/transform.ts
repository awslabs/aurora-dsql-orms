import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { runDsqlLint, type DsqlLintResult } from "./dsql-lint";

export interface TransformResult {
  sql: string;
  stderr: string;
  exitCode: number;
}

function cleanStderr(stderr: string, tempDir: string): string {
  const escapedDir = tempDir.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const tempFilePattern = new RegExp(`${escapedDir}/input\\.sql:\\d+: `, "g");
  return stderr
    .replace(tempFilePattern, "")
    .replace(new RegExp(`${escapedDir}/output\\.sql`, "g"), "<output>")
    .split("\n")
    .filter(
      (line) =>
        !line.startsWith("Fixed output written to:") &&
        !line.startsWith("Fixed output is empty") &&
        !line.startsWith("Partial fix written to:") &&
        !line.startsWith("Fix complete:") &&
        !line.startsWith("Note: SQL comments"),
    )
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function transformMigration(sql: string): TransformResult {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "dsql-transform-"));
  const inputFile = path.join(tempDir, "input.sql");
  const outputFile = path.join(tempDir, "output.sql");

  try {
    fs.writeFileSync(inputFile, sql);
    const result = runDsqlLint(["--fix", "-o", outputFile, inputFile]);
    const outputSql = fs.existsSync(outputFile)
      ? fs.readFileSync(outputFile, "utf-8")
      : "";

    return {
      sql: outputSql,
      stderr: cleanStderr(result.stderr, tempDir),
      exitCode: result.exitCode,
    };
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

export function lintMigration(sqlFile: string): DsqlLintResult {
  return runDsqlLint([sqlFile]);
}
