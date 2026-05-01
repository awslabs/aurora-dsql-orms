import { runDsqlLintWithStdin, type DsqlLintJsonOutput } from "./dsql-lint";

export interface TransformResult {
  sql: string;
  output: DsqlLintJsonOutput;
  exitCode: number;
}

export function transformMigration(sql: string): TransformResult {
  const result = runDsqlLintWithStdin(sql, ["--fix"]);
  const fixedSql = result.output.files[0]?.fixed_sql ?? "";
  return {
    sql: fixedSql,
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
