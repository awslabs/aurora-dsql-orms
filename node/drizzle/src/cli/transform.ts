import { runDsqlLintWithStdin, type DsqlLintJsonOutput } from "./dsql-lint";
import { isMultiStatement } from "../sql-statements";

/** Drizzle-kit separates statements in a migration file with this marker. */
export const BREAKPOINT = "--> statement-breakpoint";

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

// Higher rank = more severe: unfixable (1) > any unexpected code > usage
// error (2) > fixed-with-warning (3) > clean (0).
function exitRank(code: number): number {
  switch (code) {
    case 0:
      return 0;
    case 3:
      return 1;
    case 2:
      return 2;
    case 1:
      return 4;
    default:
      return 3;
  }
}

/** Return whichever exit code is more severe. */
export function worseExitCode(a: number, b: number): number {
  return exitRank(b) > exitRank(a) ? b : a;
}

// An identifier: quoted ("" escapes a quote) or bare, optionally schema-qualified.
const IDENT = String.raw`(?:"(?:[^"]|"")*"|[A-Za-z_][\w$]*)(?:\.(?:"(?:[^"]|"")*"|[A-Za-z_][\w$]*))?`;
const NOT_VALID_FK_RE = new RegExp(
  String.raw`^\s*ALTER\s+TABLE\s+(?:ONLY\s+)?(${IDENT})\s+ADD\s+CONSTRAINT\s+(${IDENT})\s+FOREIGN\s+KEY[\s\S]*NOT\s+VALID\s*;?\s*$`,
  "i",
);

/**
 * For an `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY ... NOT VALID`
 * statement, return the companion `ALTER TABLE ASYNC ... VALIDATE CONSTRAINT`
 * statement that validates the rows that already exist. Returns undefined for
 * any other statement.
 */
function validationStatementFor(statement: string): string | undefined {
  const match = NOT_VALID_FK_RE.exec(statement);
  if (!match) {
    return undefined;
  }
  return `ALTER TABLE ASYNC ${match[1]} VALIDATE CONSTRAINT ${match[2]};`;
}

export interface FileTransformResult {
  sql: string;
  exitCode: number;
  outputs: DsqlLintJsonOutput[];
}

/**
 * Transform a whole migration file for DSQL. Drizzle splits statements with
 * `--> statement-breakpoint`; each statement is transformed independently and
 * the markers are re-inserted so the runtime migrator can still split the file.
 * Statements that dsql-lint removes entirely are dropped. A foreign key that
 * ends up `NOT VALID` is followed by an `ALTER TABLE ASYNC ... VALIDATE
 * CONSTRAINT` statement so existing rows are validated by the migrator.
 */
export function transformMigrationFile(sql: string): FileTransformResult {
  if (!sql.includes(BREAKPOINT)) {
    // No breakpoints: the whole file is one chunk. If it holds more than one
    // statement (a migration generated with Drizzle Kit `breakpoints: false`),
    // the runtime migrator would send multiple DDLs in a single db.execute(),
    // which Aurora DSQL rejects (one DDL per transaction). Fail here with a
    // clear message rather than emit an unsplittable file.
    if (isMultiStatement(sql)) {
      throw new Error(
        "Migration contains multiple SQL statements but no " +
          `\`${BREAKPOINT}\` markers. Aurora DSQL allows only one DDL per ` +
          "transaction, and this adapter applies one statement per marker. " +
          "Regenerate with Drizzle Kit `breakpoints: true` (the default) so " +
          "each statement is separated by a marker. " +
          "See https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-ddl.html",
      );
    }
    const result = transformMigration(sql);
    const validation = validationStatementFor(result.sql);
    return {
      sql: validation
        ? `${result.sql.trim()}\n${BREAKPOINT}\n${validation}\n`
        : result.sql,
      exitCode: result.exitCode,
      outputs: [result.output],
    };
  }

  const parts: string[] = [];
  const outputs: DsqlLintJsonOutput[] = [];
  let exitCode = 0;

  for (const chunk of sql.split(BREAKPOINT)) {
    if (!chunk.trim()) {
      continue;
    }
    const result = transformMigration(chunk);
    outputs.push(result.output);
    exitCode = worseExitCode(exitCode, result.exitCode);
    const fixed = result.sql.trim();
    if (fixed) {
      parts.push(fixed);
      const validation = validationStatementFor(fixed);
      if (validation) {
        parts.push(validation);
      }
    }
  }

  const joined = parts.join(`\n${BREAKPOINT}\n`);
  return { sql: joined ? `${joined}\n` : "", exitCode, outputs };
}
