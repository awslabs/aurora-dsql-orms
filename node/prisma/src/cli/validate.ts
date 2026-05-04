/**
 * Aurora DSQL Schema Validator for Prisma
 *
 * Validates Prisma schemas for DSQL compatibility and reports issues.
 * The relationMode check is handled here (Prisma-specific). All other
 * SQL-level checks are delegated to dsql-lint by generating SQL via
 * `prisma migrate diff` and running it through dsql-lint's lint mode.
 */
import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";
import { lintMigration } from "./transform";

export interface ValidationIssue {
  message: string;
  line?: number;
  suggestion?: string;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
}

export async function validateSchema(
  schemaPath: string,
  skipSqlLint?: boolean,
): Promise<ValidationResult> {
  const issues: ValidationIssue[] = [];

  if (!fs.existsSync(schemaPath)) {
    return {
      valid: false,
      issues: [
        {
          message: `Schema file not found: ${schemaPath}`,
        },
      ],
    };
  }

  const schemaContent = fs.readFileSync(schemaPath, "utf-8");
  const lines = schemaContent.split("\n");

  checkRelationMode(schemaContent, lines, issues);

  if (!skipSqlLint) {
    await checkSqlCompatibility(schemaPath, issues);
  }

  return {
    valid: issues.length === 0,
    issues,
  };
}

function checkRelationMode(
  content: string,
  lines: string[],
  issues: ValidationIssue[],
): void {
  const hasDatasource = content.includes("datasource");
  const hasRelationMode = /relationMode\s*=\s*["']prisma["']/.test(content);

  if (hasDatasource && !hasRelationMode) {
    const datasourceLine = lines.findIndex((l) => l.includes("datasource"));
    issues.push({
      message: 'Missing relationMode = "prisma" in datasource block',
      line: datasourceLine + 1,
      suggestion:
        'Add relationMode = "prisma" to your datasource block. DSQL does not support foreign key constraints.',
    });
  }
}

async function checkSqlCompatibility(
  schemaPath: string,
  issues: ValidationIssue[],
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

  const result = lintMigration(sql);
  if (result.exitCode === 0) {
    return;
  }

  // Consume structured diagnostics directly — no regex scraping of stderr.
  for (const file of result.output.files) {
    for (const d of file.diagnostics) {
      issues.push({
        message: d.message,
        line: d.line,
        suggestion: d.suggestion,
      });
    }
    if (file.error) {
      issues.push({ message: file.error });
    }
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

  if (result.issues.length === 0) {
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

  lines.push("");
  lines.push(`✗ Validation failed: ${result.issues.length} error(s)`);

  return lines.join("\n");
}
