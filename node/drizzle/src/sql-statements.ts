// Tokenizes a SQL script so it can be split into individual statements. A naive
// split on ";" is wrong: a semicolon can live inside a quoted string, a quoted
// identifier, a comment, or a dollar-quoted body. Each alternative below
// consumes one such construct whole (so any ";" inside it is not a boundary);
// the final alternative consumes ordinary runs. Every character is matched by
// exactly one token, so joining the tokens reconstructs the input.
//
// Ported from the Aurora DSQL Tortoise adapter's `split_sql`
// (python/tortoise-orm/aurora_dsql_tortoise/common/config.py), which carries a
// dedicated edge-case suite; kept behavior-identical here.
const TOKEN_RE = new RegExp(
  [
    ";", // statement separator
    "'[^']*(?:''[^']*)*'", // single-quoted string ('' is an escaped quote)
    '"[^"]*(?:""[^"]*)*"', // double-quoted identifier ("" is escaped)
    "\\$\\$.*?\\$\\$", // dollar-quoted string, no tag
    "\\$(?<tag>[a-zA-Z_]\\w*)\\$.*?\\$\\k<tag>\\$", // dollar-quoted, tagged
    "\\$", // lone dollar sign
    "-(?!-)", // lone dash (not the start of --)
    "/(?!\\*)", // lone slash (not the start of /*)
    "--[^\\r\\n]*", // single-line comment
    "/\\*.*?\\*/", // multi-line comment
    "[^;'\"$/-]+", // everything else
  ].join("|"),
  "gs",
);

/**
 * Split a SQL script into individual statements on top-level semicolons,
 * ignoring semicolons inside strings, quoted identifiers, comments, and
 * dollar-quoted bodies. Statements are trimmed; empty ones (e.g. from a
 * trailing or doubled `;`) are dropped.
 */
export function splitSqlStatements(sql: string): string[] {
  const result: string[] = [];
  let current = "";
  for (const match of sql.matchAll(TOKEN_RE)) {
    const token = match[0];
    if (token === ";") {
      const statement = current.trim();
      if (statement) {
        result.push(statement);
      }
      current = "";
    } else {
      current += token;
    }
  }
  const statement = current.trim();
  if (statement) {
    result.push(statement);
  }
  return result;
}

/** True if `sql` contains more than one top-level SQL statement. */
export function isMultiStatement(sql: string): boolean {
  return splitSqlStatements(sql).length > 1;
}
