#!/usr/bin/env node
import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";
import {
  lintMigration,
  transformMigrationFile,
  worseExitCode,
} from "./transform";
import type { DsqlLintJsonOutput } from "./dsql-lint";

const HELP = `
Aurora DSQL Drizzle Tools

Usage:
  aurora-dsql-drizzle generate [-- <drizzle-kit args>]   Generate + transform migrations
  aurora-dsql-drizzle transform [input] [-o output]      Transform a migration for DSQL
  aurora-dsql-drizzle lint [input]                        Lint a migration for DSQL

Commands:
  generate [--out <dir>] [-- <drizzle-kit args>]
    The recommended way to create a migration: it runs \`drizzle-kit generate\`
    (forwarding args after \`--\`), then rewrites the generated SQL for DSQL with
    dsql-lint --fix, so one command covers the whole workflow. --out is the
    migrations dir to transform (default: ./drizzle). Re-running is safe — the
    transform is idempotent.

    Reach for \`transform\` or \`lint\` only when you need a step on its own, e.g.
    checking migrations you already have in CI.

  transform [input] [-o output]
    Transforms SQL migrations to be DSQL-compatible using dsql-lint --fix.
    Preserves Drizzle's \`--> statement-breakpoint\` markers. Reads stdin / writes
    stdout when no file is given.

  lint [input]
    Lints a SQL migration file for DSQL compatibility using dsql-lint.

Exit codes (generate / transform / lint):
  0  Clean, or all fixes applied without warnings
  1  Unfixable errors remain — review the diagnostics and fix manually
  2  Usage error (invalid arguments, propagated from dsql-lint)
  3  Fixes applied, but some produced advisories (e.g. foreign keys removed).
     The migration is written; review the warnings before applying.
`;

function rejectUnknownFlags(args: string[], knownFlags: Set<string>): void {
  for (const arg of args) {
    if (arg.startsWith("-") && !knownFlags.has(arg)) {
      console.error(`Error: Unknown flag: ${arg}`);
      process.exit(1);
    }
  }
}

/**
 * Walk the dsql-lint JSON output and emit human-readable lines on stderr.
 * Labels match dsql-lint's own text mode. See `severityFor` for the
 * (small, open) label set.
 */
function reportDsqlLintDiagnostics(output: DsqlLintJsonOutput): void {
  for (const file of output.files) {
    if (file.error) {
      console.error(`${file.file}: ${file.error}`);
      continue;
    }
    for (const d of file.diagnostics) {
      const severity = severityFor(d.fix_result.status);
      console.error(`${file.file}:${d.line}: ${severity} — ${d.message}`);
      if (d.fix_result.status !== "unfixable" && "detail" in d.fix_result) {
        console.error(`  ${d.fix_result.detail}`);
      } else if (d.suggestion) {
        console.error(`  → ${d.suggestion}`);
      }
    }
  }
}

/**
 * Maps a dsql-lint fix_result.status to a severity label. The three known
 * statuses map to ERROR / WARNING / FIXED; an unknown status from a future
 * dsql-lint falls back to INFO so output keeps rendering.
 */
function severityFor(status: string): string {
  switch (status) {
    case "unfixable":
      return "ERROR";
    case "fixed_with_warning":
      return "WARNING";
    case "fixed":
      return "FIXED";
    default:
      return "INFO";
  }
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  if (args.length === 0 || args[0] === "--help" || args[0] === "-h") {
    console.log(HELP);
    process.exit(0);
  }

  const command = args[0];

  switch (command) {
    case "generate":
      handleGenerate(args.slice(1));
      break;
    case "transform":
      await handleTransform(args.slice(1));
      break;
    case "lint":
      handleLint(args.slice(1));
      break;
    default:
      console.error(`Unknown command: ${command}`);
      console.log(HELP);
      process.exit(1);
  }
}

function handleGenerate(args: string[]): void {
  if (args.includes("--help") || args.includes("-h")) {
    console.log(`
DSQL Migration Generator

Usage:
  aurora-dsql-drizzle generate [--out <dir>] [-- <drizzle-kit args>]

Runs \`drizzle-kit generate\` and rewrites the generated SQL for DSQL.

Options:
  --out <dir>    Migrations directory to transform (default: ./drizzle)
  -h, --help     Show this help message

Everything after \`--\` is forwarded to drizzle-kit, e.g.:
  aurora-dsql-drizzle generate --out ./drizzle -- --config drizzle.config.ts
`);
    process.exit(0);
  }

  const separator = args.indexOf("--");
  const ownArgs = separator === -1 ? args : args.slice(0, separator);
  const kitArgs = separator === -1 ? [] : args.slice(separator + 1);

  rejectUnknownFlags(ownArgs, new Set(["--out", "-h", "--help"]));

  let outDir = "drizzle";
  for (let i = 0; i < ownArgs.length; i++) {
    if (ownArgs[i] === "--out") {
      const value = ownArgs[++i];
      if (!value || value.startsWith("-")) {
        console.error("Error: --out requires a directory argument");
        process.exit(1);
      }
      outDir = value;
    }
  }

  console.log("Generating migration (drizzle-kit generate)...");
  try {
    // Pass args as an argv array (no shell) so values with spaces or shell
    // metacharacters are forwarded literally, not re-split or interpreted.
    execFileSync("npx", ["drizzle-kit", "generate", ...kitArgs], {
      stdio: "inherit",
    });
  } catch {
    console.error("Error: drizzle-kit generate failed.");
    process.exit(1);
  }

  if (!fs.existsSync(outDir)) {
    console.error(
      `Error: migrations directory not found: ${outDir}\n` +
        "Pass --out <dir> matching your drizzle.config.ts `out` setting.",
    );
    process.exit(1);
  }

  const sqlFiles = fs
    .readdirSync(outDir)
    .filter((f) => f.endsWith(".sql"))
    .sort();

  console.log("Transforming for DSQL compatibility (dsql-lint --fix)...");
  let worst = 0;
  for (const file of sqlFiles) {
    const filePath = path.join(outDir, file);
    const result = transformMigrationFile(fs.readFileSync(filePath, "utf-8"));
    result.outputs.forEach(reportDsqlLintDiagnostics);
    worst = worseExitCode(worst, result.exitCode);
    if (result.exitCode === 1) {
      console.error(
        `\n✗ ${filePath}: unfixable statements remain. Review the errors above.`,
      );
      continue;
    }
    fs.writeFileSync(filePath, result.sql);
    console.log(`✓ ${filePath}`);
  }

  if (worst === 3) {
    console.log(
      "\n(dsql-lint produced warnings — review the advisories above.)",
    );
  }
  // Propagate any non-zero code (unfixable 1, usage 2, warnings 3, or an
  // unexpected code) so CI never sees success on an incomplete transform.
  if (worst !== 0) {
    process.exit(worst);
  }
}

async function handleTransform(args: string[]): Promise<void> {
  if (args.includes("--help") || args.includes("-h")) {
    console.log(`
Migration Transformer - Convert SQL migrations for Aurora DSQL

Uses dsql-lint --fix under the hood.

Usage:
  aurora-dsql-drizzle transform [input.sql] [-o output.sql]

Options:
  -o, --output <file>   Write output to file instead of stdout
  -h, --help            Show this help message
`);
    process.exit(0);
  }

  rejectUnknownFlags(args, new Set(["-o", "--output", "-h", "--help"]));

  let inputFile: string | undefined;
  let outputFile: string | undefined;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "-o" || arg === "--output") {
      const value = args[++i];
      if (!value || value.startsWith("-")) {
        console.error("Error: -o/--output requires a file argument");
        process.exit(1);
      }
      outputFile = value;
    } else if (arg && !arg.startsWith("-")) {
      inputFile = arg;
    }
  }

  let sql: string;
  if (inputFile) {
    if (!fs.existsSync(inputFile)) {
      console.error(`Error: Input file not found: ${inputFile}`);
      process.exit(1);
    }
    sql = fs.readFileSync(inputFile, "utf-8");
  } else {
    sql = await readStdin();
    if (!sql.trim()) {
      console.error("Error: No input provided");
      console.error(
        "Usage: aurora-dsql-drizzle transform [input.sql] [-o output.sql]",
      );
      process.exit(1);
    }
  }

  const result = transformMigrationFile(sql);
  result.outputs.forEach(reportDsqlLintDiagnostics);

  // Exit 1 = unfixable, exit 3 = fixed-with-warnings (still a usable
  // migration). Any other non-zero is unexpected (clap usage = 2, native
  // crash = 101, ...). Propagate before writing so we never write a partial
  // output file on an unknown exit code.
  if (result.exitCode !== 0 && result.exitCode !== 3) {
    process.exit(result.exitCode);
  }

  if (outputFile) {
    fs.writeFileSync(outputFile, result.sql);
  } else {
    process.stdout.write(result.sql);
  }

  if (result.exitCode === 3) {
    process.exit(3);
  }
}

function handleLint(args: string[]): void {
  if (args.includes("--help") || args.includes("-h")) {
    console.log(`
Migration Linter - Check SQL migrations for Aurora DSQL compatibility

Uses dsql-lint under the hood.

Usage:
  aurora-dsql-drizzle lint <input.sql>

Options:
  -h, --help    Show this help message
`);
    process.exit(0);
  }

  rejectUnknownFlags(args, new Set(["-h", "--help"]));

  const inputFile = args.find((a) => !a.startsWith("-"));
  if (!inputFile) {
    console.error("Error: Input file required");
    console.error("Usage: aurora-dsql-drizzle lint <input.sql>");
    process.exit(1);
  }

  if (!fs.existsSync(inputFile)) {
    console.error(`Error: Input file not found: ${inputFile}`);
    process.exit(1);
  }

  const sql = fs.readFileSync(inputFile, "utf-8");
  const result = lintMigration(sql);
  reportDsqlLintDiagnostics(result.output);
  process.exit(result.exitCode);
}

function readStdin(): Promise<string> {
  return new Promise((resolve, reject) => {
    if (process.stdin.isTTY) {
      resolve("");
      return;
    }

    let data = "";
    process.stdin.setEncoding("utf-8");
    process.stdin.on("data", (chunk: string) => {
      data += chunk;
    });
    process.stdin.on("end", () => {
      resolve(data);
    });
    // Without this a stdin read error (EPIPE, broken pipe) would never settle
    // the promise and the CLI would hang forever.
    process.stdin.on("error", reject);
  });
}

main().catch((error) => {
  console.error("Error:", error.message);
  process.exit(1);
});
