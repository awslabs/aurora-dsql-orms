#!/usr/bin/env node
import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";
import { validateSchema, formatValidationResult } from "./validate";
import { transformMigration, lintMigration } from "./transform";
import type { DsqlLintJsonOutput } from "./dsql-lint";

const HELP = `
Aurora DSQL Prisma Tools

Usage:
  npm run dsql-migrate <schema> -o <output>    Validate, generate, and transform migration
  npm run validate <schema>                    Validate schema for DSQL compatibility
  npm run dsql-transform [input] [-o output]   Transform migration for DSQL (via dsql-lint)
  npm run dsql-lint [input]                    Lint migration for DSQL compatibility

Commands:
  migrate <schema> -o <output> [--from-url <url>]
    All-in-one command: validates schema, generates migration, and transforms for DSQL.
    Uses dsql-lint --fix for SQL transformation.

  validate <schema>
    Validates a Prisma schema file for DSQL compatibility.
    Generates SQL and checks it with dsql-lint.

  transform [input] [-o output]
    Transforms SQL migrations to be DSQL-compatible using dsql-lint --fix.
    If no input file is specified, reads from stdin.
    If no output file is specified, writes to stdout.

  lint [input]
    Lints a SQL migration file for DSQL compatibility using dsql-lint.

Examples:
  # All-in-one migration (recommended)
  npm run dsql-migrate prisma/schema.prisma -o prisma/migrations/001_init/migration.sql

  # Incremental migration (after schema changes)
  npm run dsql-migrate prisma/schema.prisma -o prisma/migrations/002_changes/migration.sql --from-config-datasource

  # Manual workflow
  npm run validate prisma/schema.prisma
  npx prisma migrate diff --from-empty --to-schema prisma/schema.prisma --script > raw.sql
  npm run dsql-transform raw.sql -o migration.sql
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
 * Labels match dsql-lint's own text mode: ERROR / WARNING / INFO / FIXED.
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
    case "migrate": {
      await handleMigrate(args.slice(1));
      break;
    }

    case "validate": {
      const subArgs = args.slice(1);
      rejectUnknownFlags(subArgs, new Set(["-h", "--help"]));

      const schemaPath = subArgs.find((a) => !a.startsWith("-"));
      if (!schemaPath) {
        console.error("Error: Schema path required");
        console.error("Usage: npm run validate <schema>");
        process.exit(1);
      }

      const result = await validateSchema(schemaPath);
      console.log(formatValidationResult(result, schemaPath));
      process.exit(result.valid ? 0 : 1);
      break;
    }

    case "transform": {
      await handleTransform(args.slice(1));
      break;
    }

    case "lint": {
      handleLint(args.slice(1));
      break;
    }

    default:
      console.error(`Unknown command: ${command}`);
      console.log(HELP);
      process.exit(1);
  }
}

async function handleMigrate(args: string[]): Promise<void> {
  if (args.includes("--help") || args.includes("-h")) {
    console.log(`
DSQL Migration Generator - All-in-one migration workflow

Usage:
  npm run dsql-migrate <schema.prisma> -o <output.sql> [--from-url <url>]

Options:
  -o, --output <file>          Output file for the migration (required)
  --from-url <url>             Compare against existing database
  --from-config-datasource     Compare against datasource in prisma.config.ts
  --from-empty                 Generate from empty (default)
  -h, --help                   Show this help message

This command:
  1. Validates your schema for DSQL compatibility
  2. Generates migration SQL using Prisma
  3. Transforms the SQL for DSQL compatibility using dsql-lint

Examples:
  # Initial migration
  npm run dsql-migrate prisma/schema.prisma -o prisma/migrations/001_init/migration.sql

  # Incremental migration (after schema changes)
  npm run dsql-migrate prisma/schema.prisma -o prisma/migrations/002_changes/migration.sql --from-config-datasource
`);
    process.exit(0);
  }

  const knownFlags = new Set([
    "-o",
    "--output",
    "--from-url",
    "--from-config-datasource",
    "--from-empty",
    "-h",
    "--help",
  ]);
  rejectUnknownFlags(args, knownFlags);

  let schemaPath: string | undefined;
  let outputFile: string | undefined;
  let fromUrl: string | undefined;
  let fromConfigDatasource = false;
  let fromEmpty = false;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "-o" || arg === "--output") {
      outputFile = args[++i];
    } else if (arg === "--from-url") {
      fromUrl = args[++i];
      if (!fromUrl || fromUrl.startsWith("-")) {
        console.error("Error: --from-url requires a URL argument");
        process.exit(1);
      }
    } else if (arg === "--from-config-datasource") {
      fromConfigDatasource = true;
    } else if (arg === "--from-empty") {
      fromEmpty = true;
    } else if (arg && !arg.startsWith("-")) {
      schemaPath = arg;
    }
  }

  if (!schemaPath) {
    console.error("Error: Schema path required");
    console.error(
      "Usage: npm run dsql-migrate <schema.prisma> -o <output.sql>",
    );
    process.exit(1);
  }

  if (!outputFile) {
    console.error("Error: Output file required");
    console.error(
      "Usage: npm run dsql-migrate <schema.prisma> -o <output.sql>",
    );
    process.exit(1);
  }

  if (!fromUrl && !fromConfigDatasource && !fromEmpty) {
    fromEmpty = true;
  }

  // Step 1: Validate schema
  console.log(`Validating ${path.basename(schemaPath)}...`);
  const validationResult = await validateSchema(schemaPath, true);

  if (!validationResult.valid) {
    console.log(formatValidationResult(validationResult, schemaPath));
    console.error("\nFix the schema errors above and re-run.");
    process.exit(1);
  }

  console.log(`✓ Schema is DSQL-compatible`);

  // Step 2: Generate migration using Prisma
  const fromSource = fromUrl || fromConfigDatasource ? "database" : "empty";
  console.log(`\nGenerating migration (from ${fromSource})...`);

  let fromArg: string;
  if (fromUrl) {
    fromArg = `--from-url "${fromUrl}"`;
  } else if (fromConfigDatasource) {
    fromArg = "--from-config-datasource";
  } else {
    fromArg = "--from-empty";
  }
  const prismaCmd = `npx prisma migrate diff ${fromArg} --to-schema "${schemaPath}" --script`;

  let rawSql: string;
  try {
    rawSql = execSync(prismaCmd, {
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    });
  } catch (error: unknown) {
    const execError = error as { stderr?: string; message?: string };
    console.error("Error generating migration:");
    console.error(execError.stderr || execError.message);
    process.exit(1);
  }

  if (!rawSql.trim() || rawSql.trim() === "-- This is an empty migration.") {
    console.log("\n✓ No changes detected - schema is up to date");
    process.exit(0);
  }

  // Step 3: Transform for DSQL using dsql-lint
  console.log("Transforming for DSQL compatibility (dsql-lint --fix)...");
  const transformResult = transformMigration(rawSql);

  reportDsqlLintDiagnostics(transformResult.output);

  // Exit 1: unfixable errors or I/O errors. Exit 3: all fixed but some
  // produced warnings (e.g. removed FK) — still a successful transform.
  if (transformResult.exitCode === 1) {
    console.error(
      "\n✗ dsql-lint failed with unfixable errors. Review the errors above.",
    );
    process.exit(1);
  }

  // Ensure output directory exists
  const outputDir = path.dirname(outputFile);
  if (outputDir && !fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  fs.writeFileSync(outputFile, transformResult.sql);
  console.log(`\n✓ Migration written to: ${outputFile}`);
  if (transformResult.exitCode === 3) {
    console.log(
      "  (dsql-lint produced warnings — review the advisories above.)",
    );
  }
}

async function handleTransform(args: string[]): Promise<void> {
  if (args.includes("--help") || args.includes("-h")) {
    console.log(`
Migration Transformer - Convert SQL migrations for Aurora DSQL

Uses dsql-lint --fix under the hood.

Usage:
  npm run dsql-transform [input.sql] [-o output.sql]

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
      outputFile = args[++i];
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
        "Usage: npm run dsql-transform [input.sql] [-o output.sql]",
      );
      process.exit(1);
    }
  }

  const result = transformMigration(sql);

  reportDsqlLintDiagnostics(result.output);

  // Exit 1 = unfixable; exit 3 = fixed-with-warnings (still a usable
  // migration). Propagate the code so callers / CI can distinguish.
  if (result.exitCode === 1) {
    process.exit(1);
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
  npm run dsql-lint <input.sql>

Options:
  -h, --help    Show this help message
`);
    process.exit(0);
  }

  rejectUnknownFlags(args, new Set(["-h", "--help"]));

  const inputFile = args.find((a) => !a.startsWith("-"));
  if (!inputFile) {
    console.error("Error: Input file required");
    console.error("Usage: npm run dsql-lint <input.sql>");
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
  return new Promise((resolve) => {
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
  });
}

main().catch((error) => {
  console.error("Error:", error.message);
  process.exit(1);
});
