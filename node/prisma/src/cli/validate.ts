/**
 * Aurora DSQL Schema Validator for Prisma
 *
 * Validates Prisma schemas for DSQL compatibility and reports issues.
 * SQL-level checks are delegated to dsql-lint by generating SQL via
 * `prisma migrate diff` and running it through the same dsql-lint fix path
 * used to transform migrations.
 */
import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";
import { transformMigration } from "./transform";

export interface ValidationIssue {
  message: string;
  line?: number;
  suggestion?: string;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
  advisories: ValidationIssue[];
}

export async function validateSchema(
  schemaPath: string,
  skipSqlLint?: boolean,
): Promise<ValidationResult> {
  const issues: ValidationIssue[] = [];
  const advisories: ValidationIssue[] = [];

  if (!fs.existsSync(schemaPath)) {
    return {
      valid: false,
      advisories,
      issues: [
        {
          message: `Schema file not found: ${schemaPath}`,
        },
      ],
    };
  }

  if (!skipSqlLint) {
    await checkSqlCompatibility(schemaPath, issues, advisories);
  }

  return {
    valid: issues.length === 0,
    issues,
    advisories,
  };
}

async function checkSqlCompatibility(
  schemaPath: string,
  issues: ValidationIssue[],
  advisories: ValidationIssue[],
): Promise<void> {
  let sql: string;
  try {
    sql = execSync(
      `npx prisma migrate diff --from-empty --to-schema "${schemaPath}" --script`,
      { encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] },
    );
  } catch (error: unknown) {
    const execError = error as { stderr?: string };
    const stderr = execError.stderr ?? "";
    const errorLine =
      stderr
        .split("\n")
        .find((l) => /^error:/.test(l.trim()))
        ?.trim() ?? "";
    issues.push({
      message: errorLine || "Failed to generate SQL from schema",
    });
    return;
  }

  if (!sql.trim() || sql.trim() === "-- This is an empty migration.") {
    return;
  }

  const result = transformMigration(sql);

  // Consume structured diagnostics directly — no regex scraping of stderr.
  for (const file of result.output.files) {
    for (const d of file.diagnostics) {
      const issue = {
        message: d.message,
        line: d.line,
        suggestion:
          d.fix_result.status !== "unfixable" && "detail" in d.fix_result
            ? d.fix_result.detail
            : d.suggestion,
      };
      (d.fix_result.status === "unfixable" ? issues : advisories).push(issue);
    }
    if (file.error) {
      issues.push({ message: file.error });
    }
  }

  if (result.exitCode !== 0 && result.exitCode !== 1 && result.exitCode !== 3) {
    issues.push({ message: `dsql-lint exited with code ${result.exitCode}` });
  } else if (result.exitCode === 1 && issues.length === 0) {
    issues.push({ message: "dsql-lint reported an unfixable error" });
  }
}

/**
 * Formats validation results for console output.
 */
export function formatValidationResult(
  result: ValidationResult,
  schemaPath: string,
): string {
  const lines: string[] = [];
  const fileName = path.basename(schemaPath);

  if (result.issues.length === 0 && result.advisories.length === 0) {
    lines.push(`✓ ${fileName}: Schema is DSQL-compatible`);
    return lines.join("\n");
  }

  lines.push(`Validating ${fileName}...`);
  lines.push("");

  for (const issue of result.issues) {
    const lineInfo = issue.line ? ` (line ${issue.line})` : "";
    lines.push(`✗ ${issue.message}${lineInfo}`);
    if (issue.suggestion) {
      lines.push(`  → ${issue.suggestion}`);
    }
  }

  for (const advisory of result.advisories) {
    const lineInfo = advisory.line ? ` (line ${advisory.line})` : "";
    lines.push(`⚠ ${advisory.message}${lineInfo}`);
    if (advisory.suggestion) {
      lines.push(`  → ${advisory.suggestion}`);
    }
  }

  lines.push("");
  if (result.issues.length > 0) {
    lines.push(`✗ Validation failed: ${result.issues.length} error(s)`);
  } else {
    const suffix = result.advisories.length === 1 ? "advisory" : "advisories";
    lines.push(
      `✓ Validation passed with ${result.advisories.length} ${suffix}`,
    );
  }

  return lines.join("\n");
}
