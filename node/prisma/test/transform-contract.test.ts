import {
  runDsqlLintWithStdin,
  type DsqlLintDiagnostic,
  type DsqlLintJsonOutput,
} from "../src/cli/dsql-lint";
import { transformMigration } from "../src/cli/transform";

jest.mock("../src/cli/dsql-lint");

const lint = jest.mocked(runDsqlLintWithStdin);
const sql =
  'CREATE TABLE "a" ("id" UUID PRIMARY KEY); CREATE TABLE "b" ("id" UUID PRIMARY KEY);';

function response(fixedSql: string, diagnostics: DsqlLintDiagnostic[] = []) {
  const errors = diagnostics.filter(
    (entry) => entry.fix_result.status === "unfixable",
  ).length;
  const warnings = diagnostics.filter(
    (entry) => entry.fix_result.status === "fixed_with_warning",
  ).length;
  const output: DsqlLintJsonOutput = {
    schema_version: 1,
    files: [
      {
        file: "<stdin>",
        diagnostics,
        error: null,
        output_file: null,
        fixed_sql: fixedSql,
      },
    ],
    summary: { errors, warnings, fixed: 0 },
  };
  return { exitCode: errors > 0 ? 1 : warnings > 0 ? 3 : 0, output };
}

function diagnostic(
  rule: string,
  status: "fixed_with_warning" | "unfixable",
): DsqlLintDiagnostic {
  return {
    rule,
    line: 1,
    message: "test diagnostic",
    suggestion: "",
    statement_preview: "BEGIN;",
    fix_result:
      status === "unfixable" ? { status } : { status, detail: "test fix" },
  };
}

beforeEach(() => lint.mockReset());

test.each(["commit", "end", "ROLLBACK", "ABORT", "rollback", "abort"])(
  "passes a script ending with %s directly to the linter without wrapping",
  (end) => {
    const input = `${sql} ${end};`;
    lint.mockReturnValue(response("unchanged"));
    expect(transformMigration(input).sql).toBe("unchanged");
    expect(lint).toHaveBeenCalledTimes(1);
    expect(lint).toHaveBeenCalledWith(input, ["--fix"]);
  },
);

// The mock isolates the JSON status boundary from dsql-lint's SQL parsing.
test.each(["multi_ddl_transaction", "mixed_ddl_dml_transaction"])(
  "does not treat an unfixable %s diagnostic as a completed split",
  (rule) => {
    lint
      .mockReturnValueOnce(response("wrapped", [diagnostic(rule, "unfixable")]))
      .mockReturnValueOnce(response("unwrapped"));
    expect(transformMigration(sql).sql).toBe("unwrapped");
    expect(lint).toHaveBeenCalledTimes(2);
    expect(lint).toHaveBeenLastCalledWith(sql, ["--fix"]);
  },
);

test("fails clearly rather than discarding a renamed wrapper-dependent split fix", () => {
  lint
    .mockReturnValueOnce(
      response("split", [diagnostic("renamed_split", "fixed_with_warning")]),
    )
    .mockReturnValueOnce(response("unsplit"));
  expect(() => transformMigration(sql)).toThrow(
    /unrecognized transaction-dependent fix \(renamed_split\)/,
  );
});

test("allows an unknown fix present in both wrapped and unwrapped runs", () => {
  const fix = diagnostic("new_compatibility_rule", "fixed_with_warning");
  lint
    .mockReturnValueOnce(response("wrapped", [fix]))
    .mockReturnValueOnce(response("unwrapped", [fix]));
  expect(transformMigration(sql).sql).toBe("unwrapped");
});

test("keeps a recognized completed split without running the fallback", () => {
  lint.mockReturnValueOnce(
    response("split", [
      diagnostic("multi_ddl_transaction", "fixed_with_warning"),
    ]),
  );
  expect(transformMigration(sql).sql).toBe("split");
  expect(lint).toHaveBeenCalledTimes(1);
});
