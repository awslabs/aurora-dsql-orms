import { runDsqlLintWithStdin, type DsqlLintJsonOutput } from "./dsql-lint";

export interface TransformResult {
  sql: string;
  output: DsqlLintJsonOutput;
  exitCode: number;
  advisories: string[];
}

export interface TransformOptions {
  /**
   * Run the script through dsql-lint as one transaction so it is split into
   * one transaction per statement. Defaults to true.
   */
  splitTransactions?: boolean;
}

const TRANSACTION_END = /^(?:commit|end|rollback|abort)\b/i;

/**
 * Prisma can apply a migration file as a single query, which PostgreSQL runs
 * as one implicit transaction. Prisma ORM 7.3 and earlier always do; later
 * versions do when they cannot parse the file, which DSQL syntax such as
 * `CREATE INDEX ASYNC` causes. DSQL allows one DDL statement per transaction,
 * so wrapping the script in an explicit transaction lets dsql-lint split it
 * into one transaction per statement.
 *
 * Scripts that end a transaction themselves are left for dsql-lint to handle
 * as written. Wrapping a script that commits part way through would leave the
 * statements after its COMMIT unsplit. BEGIN shares the first line and the
 * closing COMMIT follows a `;` so diagnostic line numbers and a final
 * unterminated statement keep working.
 *
 * Splitting also ends settings scoped to the transaction, such as
 * `SET LOCAL search_path`, before the statements that rely on them run, so a
 * script that uses one is not wrapped. `set_config` with `false` as its third
 * argument sets the value for the session, so it does not count.
 */
function wrapInTransaction(
  sql: string,
): Pick<TransformResult, "sql" | "advisories"> {
  const statements = codeOf(sql)
    .split(";")
    .map((statement) => statement.trim())
    .filter((statement) => statement !== "");
  const reason = statements
    .map(splitSkipReason)
    .find((reason) => reason !== undefined);
  if (reason) {
    return {
      sql,
      advisories: hasStatementsOutsideTransaction(statements)
        ? [
            `Transaction splitting was skipped because the script uses ${reason}. ` +
              "Put each DDL statement in its own BEGIN/COMMIT transaction and repeat any required transaction-scoped settings before deploying.",
          ]
        : [],
    };
  }
  return { sql: `BEGIN; ${sql}\n;\nCOMMIT;\n`, advisories: [] };
}

function splitSkipReason(statement: string): string | undefined {
  const end = statement.match(TRANSACTION_END);
  if (end) return end[0].toUpperCase();
  const setting = statement.match(/^set\s+(local|constraints)\b/i);
  if (setting) return `SET ${setting[1]!.toUpperCase()}`;
  if (
    /\bset_config\s*\(/i.test(
      statement.replace(
        /\bset_config\s*\((?:[^()]|\([^()]*\))*,\s*false\s*\)/gi,
        "",
      ),
    )
  ) {
    return "set_config with a scope that is not provably session-scoped";
  }
  return undefined;
}

function hasStatementsOutsideTransaction(statements: string[]): boolean {
  let inTransaction = false;
  for (const statement of statements) {
    if (/^(?:begin\b|start\s+transaction\b)/i.test(statement)) {
      inTransaction = true;
    } else if (TRANSACTION_END.test(statement)) {
      inTransaction = false;
    } else if (!inTransaction) {
      return true;
    }
  }
  return false;
}

function splitsTransaction(output: DsqlLintJsonOutput): boolean {
  return output.files.some((file) =>
    file.diagnostics.some(
      (d) =>
        (d.rule === "multi_ddl_transaction" ||
          d.rule === "mixed_ddl_dml_transaction") &&
        d.fix_result.status !== "unfixable",
    ),
  );
}

const SQL_TOKEN = new RegExp(
  [
    String.raw`\/\*`,
    String.raw`--[^\n]*`,
    String.raw`[Ee]'(?:[^'\\]|\\[\s\S]|'')*'`,
    String.raw`'(?:[^']|'')*'`,
    String.raw`"(?:[^"]|"")*"`,
    String.raw`\$([\p{L}_][\p{L}\p{N}_]*)?\$[\s\S]*?\$\1\$`,
    String.raw`[\p{L}\p{N}_$]+`,
    String.raw`[\s\S]`,
  ].join("|"),
  "uy",
);

/**
 * The script with comments replaced by a space and string literals and
 * dollar-quoted bodies replaced by `''`, so keyword checks see only SQL code
 * and a `;` inside quoted text does not end a statement. A quoted identifier
 * keeps its name when quoting it changes nothing, such as `"set_config"`.
 */
function codeOf(sql: string): string {
  let code = "";
  let i = 0;
  while (i < sql.length) {
    SQL_TOKEN.lastIndex = i;
    const token = SQL_TOKEN.exec(sql)![0];
    if (token === "/*") {
      // Block comments nest in PostgreSQL.
      let depth = 1;
      i += 2;
      while (i < sql.length && depth > 0) {
        if (sql.startsWith("/*", i)) {
          depth++;
          i += 2;
        } else if (sql.startsWith("*/", i)) {
          depth--;
          i += 2;
        } else {
          i++;
        }
      }
      code += " ";
      continue;
    }
    i += token.length;
    if (token.startsWith("--")) {
      code += " ";
    } else if (token.startsWith('"')) {
      const name = token.slice(1, -1);
      code += /^[a-z_][a-z0-9_$]*$/.test(name) ? name : '""';
    } else if (/^(?:[Ee]?'|\$)/.test(token) && token.length > 1) {
      code += "''";
    } else {
      code += token;
    }
  }
  return code;
}

export function transformMigration(
  sql: string,
  { splitTransactions = true }: TransformOptions = {},
): TransformResult {
  const { sql: wrapped, advisories } = splitTransactions
    ? wrapInTransaction(sql)
    : { sql, advisories: [] };
  let result = runDsqlLintWithStdin(wrapped, ["--fix"]);
  if (wrapped !== sql && !splitsTransaction(result.output)) {
    // Nothing needed its own transaction, so keep the file's transactions as
    // written, for example data batches that each stay under DSQL's limits.
    const unwrapped = runDsqlLintWithStdin(sql, ["--fix"]);
    // Treat a wrapper-only fix as a possible renamed split rule so version
    // drift surfaces before deployment.
    const unexpectedFix = result.output.files
      .flatMap((file) => file.diagnostics)
      .find(
        (diagnostic) =>
          diagnostic.fix_result.status !== "unfixable" &&
          !unwrapped.output.files.some((file) =>
            file.diagnostics.some(
              (other) =>
                other.rule === diagnostic.rule &&
                other.line === diagnostic.line &&
                other.fix_result.status === diagnostic.fix_result.status,
            ),
          ),
      );
    if (unexpectedFix) {
      throw new Error(
        `dsql-lint reported an unrecognized transaction-dependent fix (${unexpectedFix.rule}). ` +
          "Check compatibility with this dsql-lint version before deploying the migration.",
      );
    }
    result = unwrapped;
  }
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
    exitCode:
      result.exitCode === 0 && advisories.length > 0 ? 3 : result.exitCode,
    advisories,
  };
}

export function lintMigration(sql: string): {
  exitCode: number;
  output: DsqlLintJsonOutput;
} {
  return runDsqlLintWithStdin(sql, []);
}
