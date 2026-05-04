import { runDsqlLintWithStdin, type DsqlLintJsonOutput } from "./dsql-lint";

export interface TransformResult {
  sql: string;
  output: DsqlLintJsonOutput;
  exitCode: number;
}

export function transformMigration(sql: string): TransformResult {
  const result = runDsqlLintWithStdin(sql, ["--fix"]);
  // On any non-error exit, dsql-lint must return the fixed SQL inline
  // (stdin + --fix contract). A missing `fixed_sql` here means either the
  // JSON schema changed or dsql-lint violated its own contract — either
  // way, failing loud is better than writing a zero-byte migration.
  const fixedSql = result.output.files[0]?.fixed_sql;
  if (fixedSql == null && result.exitCode !== 1) {
    throw new Error(
      `dsql-lint did not return fixed SQL (exit=${result.exitCode}). ` +
        `Expected files[0].fixed_sql to be populated for stdin --fix mode.`,
    );
  }
  return {
    sql: fixedSql ?? "",
    output: result.output,
    exitCode: result.exitCode,
  };
}

export function lintMigration(sql: string): {
  exitCode: number;
  output: DsqlLintJsonOutput;
} {
  return runDsqlLintWithStdin(sql, []);
}
