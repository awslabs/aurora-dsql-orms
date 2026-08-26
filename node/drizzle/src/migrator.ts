import crypto from "node:crypto";
import { sql } from "drizzle-orm";
import {
  readMigrationFiles,
  type MigrationConfig,
  type MigrationMeta,
} from "drizzle-orm/migrator";
import type { NodePgDatabase } from "drizzle-orm/node-postgres";
import { isMultiStatement } from "./sql-statements";
import { withRetry } from "./retry";

/** Minimal pg-compatible result shape returned by `db.execute`. */
interface QueryResult<T> {
  rows: T[];
  rowCount?: number;
}

/** Any Drizzle node-postgres database (schema-agnostic). */
type AnyNodePgDatabase = NodePgDatabase<Record<string, unknown>>;

interface AwsDsqlMigrationResultBase {
  /** Number of statements successfully applied this run. */
  appliedStatements: number;
  /** Total number of pending statements across all pending migrations. */
  totalStatements: number;
  /** Number of migrations fully completed this run. */
  completedMigrations: number;
  /** Total number of pending migrations. */
  totalMigrations: number;
}

/** Details captured when a migration statement fails. */
export interface AwsDsqlMigrationError {
  message: string;
  migrationName: string;
  statementIndex: number;
  sql?: string;
}

/**
 * Result of a DSQL migration run. A discriminated union so `error` is only
 * present (and required) when `success` is false.
 */
export type AwsDsqlMigrationResult =
  | (AwsDsqlMigrationResultBase & { success: true })
  | (AwsDsqlMigrationResultBase & {
      success: false;
      error: AwsDsqlMigrationError;
    });

function hashStatement(stmt: string): string {
  return crypto.createHash("sha256").update(stmt.trim()).digest("hex");
}

/**
 * Run one autocommit migration operation, retrying DSQL optimistic-concurrency
 * conflicts.
 *
 * The connector only retries work routed through `AuroraDSQLPool.transaction()`
 * — it leaves `pool.query()` (what `db.execute` ends up calling) alone — so
 * without this a single conflict from a concurrent deploy or a busy cluster
 * fails the whole migration run.
 *
 * Re-running is safe because every operation here is a single statement in its
 * own implicit transaction: a conflict means it did not commit. Retries use the
 * defaults from {@link withRetry} (3 retries after the first attempt, 50ms
 * base, 5s cap).
 */
function withOccRetry<T>(operation: () => Promise<T>): Promise<T> {
  return withRetry(operation, {
    // A retried conflict is otherwise invisible: the run just stalls for the
    // backoff and carries on, so a slow migration looks like a hung one.
    onRetry: (error, attempt, maxAttempts) => {
      const code = (error as { cause?: { code?: string } })?.cause?.code;
      console.warn(
        "Warning: optimistic-concurrency conflict" +
          `${code ? ` (${code})` : ""} during migration; ` +
          `retrying attempt ${attempt} of ${maxAttempts}.`,
      );
    },
  });
}

// DSQL's two asynchronous DDL forms. Both reply with a row `{ job_id: '...' }`
// and finish the work in the background, so the effect isn't visible until the
// job completes:
//   - CREATE [UNIQUE] INDEX ASYNC ...        (optional IF NOT EXISTS)
//   - ALTER TABLE ASYNC ... VALIDATE CONSTRAINT ...
// See https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-create-index-async.html
// and .../alter-table-syntax-support.html
const ASYNC_DDL_RE =
  /^\s*(CREATE\s+(UNIQUE\s+)?INDEX\s+ASYNC\b|ALTER\s+TABLE\s+ASYNC\b)/i;

function isAsyncDdl(stmt: string): boolean {
  return ASYNC_DDL_RE.test(stmt);
}

/**
 * Block until a DSQL asynchronous job (an index build or a constraint
 * validation) finishes. `sys.wait_for_job` is a procedure (invoked with CALL,
 * not SELECT) that blocks until the job succeeds, fails, or the wait times out,
 * returning a `succeeded` flag. Only an explicit `true` counts as success —
 * `false`, a null/unknown status (e.g. a timed-out wait), or a missing row is
 * surfaced as an error rather than recording the statement as applied.
 */
async function waitForDsqlJob(
  db: AnyNodePgDatabase,
  jobId: string,
): Promise<void> {
  // DSQL updates the catalog when the job completes, which can raise a
  // concurrency error for sessions touching the same namespace — so this wait
  // is retried like every other operation here.
  const res = (await withOccRetry(() =>
    db.execute(sql`CALL sys.wait_for_job(${jobId})`),
  )) as QueryResult<{ succeeded: boolean | null }>;
  const succeeded = res.rows[0]?.succeeded;
  if (succeeded !== true) {
    throw new Error(
      `Aurora DSQL async job ${jobId} did not succeed ` +
        `(succeeded=${succeeded ?? "unknown"}); the background job may have ` +
        "failed or the wait timed out.",
    );
  }
}

// Drizzle's MigrationMeta carries only folderMillis (not the "0000_init" tag),
// so derive a stable UTC timestamp for display in errors/warnings.
function getMigrationName(folderMillis: number): string {
  const date = new Date(folderMillis);
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  const hours = String(date.getUTCHours()).padStart(2, "0");
  const minutes = String(date.getUTCMinutes()).padStart(2, "0");
  const seconds = String(date.getUTCSeconds()).padStart(2, "0");
  return `${year}${month}${day}${hours}${minutes}${seconds}`;
}

function resolveMigrationTarget(config: string | MigrationConfig): {
  migrationsTable: string;
  migrationsSchema: string;
} {
  const cfg: Partial<MigrationConfig> =
    typeof config === "string" ? {} : config;
  return {
    migrationsTable: cfg.migrationsTable ?? "__drizzle_migrations",
    migrationsSchema: cfg.migrationsSchema ?? "drizzle",
  };
}

function readMigrations(config: string | MigrationConfig): MigrationMeta[] {
  return readMigrationFiles(
    typeof config === "string" ? { migrationsFolder: config } : config,
  );
}

/**
 * Migrate an Aurora DSQL database using statement-level tracking.
 *
 * Applies and tracks each statement individually (autocommit), matching how
 * Aurora DSQL runs DDL; the stock node-postgres `migrate()` instead sends every
 * statement in one transaction. A run that fails partway can be re-run:
 * already-applied statements are recorded in the tracking table and skipped.
 * A statement and its tracking row are two separate autocommits, so a crash in
 * the gap between them leaves the statement applied but untracked; on re-run
 * the (non-idempotent) statement is retried and its error surfaced, so the
 * migration can be reconciled manually.
 *
 * Migration SQL is expected to already be DSQL-compatible — run it through
 * `aurora-dsql-drizzle transform` (dsql-lint) at generate time; this
 * function does not rewrite statements.
 *
 * @param db A Drizzle instance created by this adapter's `drizzle()`.
 * @param config A migrations folder path or a `MigrationConfig`.
 */
export async function migrate(
  db: AnyNodePgDatabase,
  config: string | MigrationConfig,
): Promise<AwsDsqlMigrationResult> {
  return migrateInternal(db, readMigrations(config), config);
}

/**
 * Migration core, taking already-parsed migrations. Exposed for unit tests that
 * supply migrations without reading from disk.
 * @internal
 */
export async function migrateInternal(
  db: AnyNodePgDatabase,
  migrations: MigrationMeta[],
  config: string | MigrationConfig,
): Promise<AwsDsqlMigrationResult> {
  const { migrationsTable, migrationsSchema } = resolveMigrationTarget(config);

  try {
    await withOccRetry(() =>
      db.execute(
        sql`CREATE SCHEMA IF NOT EXISTS ${sql.identifier(migrationsSchema)}`,
      ),
    );
  } catch (error) {
    throw new Error(
      `Failed to create migrations schema "${migrationsSchema}". ` +
        "Ensure you have CREATE SCHEMA permission.",
      { cause: error },
    );
  }

  try {
    // DSQL requires an explicit cache size on identity columns, and allows only
    // 1 or >= 65536; CACHE 1 minimizes id gaps on this low-volume tracking
    // table.
    // Identity is (migration_folder_millis, statement_index): migration_hash
    // hashes the whole file, so editing any statement invalidates every key
    // in that migration and reruns already-applied ones. folder-millis is
    // stable across such edits. migration_hash is kept for diagnostics.
    await withOccRetry(() =>
      db.execute(sql`
      CREATE TABLE IF NOT EXISTS ${sql.identifier(migrationsSchema)}.${sql.identifier(migrationsTable)} (
        id BIGINT GENERATED ALWAYS AS IDENTITY (CACHE 1) PRIMARY KEY,
        migration_hash TEXT NOT NULL,
        migration_folder_millis BIGINT NOT NULL,
        statement_index INTEGER NOT NULL,
        statement_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (migration_folder_millis, statement_index)
      )
    `),
    );
  } catch (error) {
    throw new Error(
      `Failed to create migrations table "${migrationsSchema}.${migrationsTable}". ` +
        "Ensure you have CREATE TABLE permission.",
      { cause: error },
    );
  }

  const applied = (await withOccRetry(() =>
    db.execute(
      sql`SELECT migration_folder_millis, statement_index, statement_hash
      FROM ${sql.identifier(migrationsSchema)}.${sql.identifier(migrationsTable)}
      ORDER BY migration_folder_millis, statement_index`,
    ),
  )) as QueryResult<{
    migration_folder_millis: string | number;
    statement_index: number;
    statement_hash: string;
  }>;

  // BIGINT round-trips from pg as a string; normalize to number for the key.
  const appliedHashMap = new Map(
    applied.rows.map((row) => [
      `${Number(row.migration_folder_millis)}:${row.statement_index}`,
      row.statement_hash,
    ]),
  );

  // Records an applied statement in the tracking table. Idempotent via
  // ON CONFLICT so a retried tracking insert can't fail on the unique key.
  const recordStatement = (
    migration: MigrationMeta,
    stmtIdx: number,
    statementHash: string,
  ) =>
    withOccRetry(() =>
      db.execute(
        sql`INSERT INTO ${sql.identifier(migrationsSchema)}.${sql.identifier(migrationsTable)}
        (migration_hash, migration_folder_millis, statement_index, statement_hash)
        VALUES (${migration.hash}, ${migration.folderMillis}, ${stmtIdx}, ${statementHash})
        ON CONFLICT (migration_folder_millis, statement_index) DO NOTHING`,
      ),
    );

  let totalStatements = 0;
  let totalMigrations = 0;
  for (const migration of migrations) {
    const pending = migration.sql.filter(
      (_, idx) => !appliedHashMap.has(`${migration.folderMillis}:${idx}`),
    ).length;
    if (pending > 0) {
      totalMigrations++;
      totalStatements += pending;
    }
  }

  let appliedStatementsCount = 0;
  let completedMigrations = 0;

  /**
   * Failure text for a migration result.
   *
   * Drizzle wraps driver errors and {@link withRetry} wraps those again, so the
   * part a caller needs — the SQLSTATE and driver detail — sits at the end of
   * the `cause` chain. Reporting only the outer message turns an exhausted
   * retry into generic boilerplate with no indication of what actually failed.
   */
  const describeError = (e: unknown): string => {
    if (!(e instanceof Error)) {
      return String(e);
    }
    let cause: unknown = (e as { cause?: unknown }).cause;
    let detail: string | undefined;
    while (cause != null) {
      const link = cause as {
        message?: string;
        code?: string;
        cause?: unknown;
      };
      const parts = [link.code, link.message].filter(Boolean);
      if (parts.length > 0) {
        detail = parts.join(": ");
      }
      cause = link.cause;
    }
    return detail ? `${e.message} (${detail})` : e.message;
  };

  const fail = (
    migration: MigrationMeta,
    stmtIdx: number,
    stmt: string,
    message: string,
  ): AwsDsqlMigrationResult => ({
    success: false,
    appliedStatements: appliedStatementsCount,
    totalStatements,
    completedMigrations,
    totalMigrations,
    error: {
      message,
      migrationName: getMigrationName(migration.folderMillis),
      statementIndex: stmtIdx,
      sql:
        stmt.length > 500
          ? `${stmt.slice(0, 500)}... [truncated, ${stmt.length - 500} more chars]`
          : stmt,
    },
  });

  for (const migration of migrations) {
    let migrationHadPendingStatements = false;

    for (let stmtIdx = 0; stmtIdx < migration.sql.length; stmtIdx++) {
      const stmtKey = `${migration.folderMillis}:${stmtIdx}`;
      const rawStmt = migration.sql[stmtIdx]!;
      const currentStmtHash = hashStatement(rawStmt);

      if (appliedHashMap.has(stmtKey)) {
        const storedHash = appliedHashMap.get(stmtKey);
        if (storedHash && storedHash !== currentStmtHash) {
          console.warn(
            `Warning: statement ${stmtIdx} in migration ${getMigrationName(migration.folderMillis)} ` +
              `has changed since it was applied (stored ${storedHash.slice(0, 8)}... ` +
              `vs current ${currentStmtHash.slice(0, 8)}...). It will be skipped.\n` +
              "Action: if the change is intentional, create a new migration.",
          );
        }
        continue;
      }

      migrationHadPendingStatements = true;
      const stmt = rawStmt.trim();

      // Empty chunk (e.g. trailing statement-breakpoint) — still track it so
      // statement indices stay aligned with the file on the next run.
      if (!stmt) {
        await recordStatement(migration, stmtIdx, currentStmtHash);
        appliedStatementsCount++;
        continue;
      }

      // Reject a chunk holding more than one statement. Aurora DSQL runs one
      // DDL per implicit transaction and this migrator applies one statement
      // per chunk, so a multi-statement chunk (a migration generated with
      // Drizzle Kit `breakpoints: false`) would otherwise be sent in a single
      // db.execute() and rejected by DSQL with a cryptic error. Fail early and
      // clearly instead.
      if (isMultiStatement(stmt)) {
        return fail(
          migration,
          stmtIdx,
          stmt,
          "Statement chunk contains multiple SQL statements. Aurora DSQL allows " +
            "only one DDL per transaction, and this migrator applies one " +
            "statement per chunk. Regenerate with Drizzle Kit `breakpoints: true` " +
            "(the default) so each statement is separated by a " +
            "`--> statement-breakpoint` marker. " +
            "See https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-ddl.html",
        );
      }

      try {
        const execResult = (await withOccRetry(() =>
          db.execute(sql.raw(stmt)),
        )) as QueryResult<Record<string, unknown>>;

        // Asynchronous DDL returns immediately with a job_id while the work
        // runs in the background. Block until the job completes so a follow-up
        // migration (or the caller) can rely on it having taken effect, and so
        // a failed job is never recorded as applied.
        //
        // A skipped statement returns no rows at all: `CREATE INDEX ASYNC IF
        // NOT EXISTS` on an existing index starts no build, so there is nothing
        // to await and it stays a success. Only a row that came back without a
        // usable job_id is unexpected.
        const rows = execResult.rows ?? [];
        const jobId = rows[0]?.["job_id"];
        if (typeof jobId === "string" && jobId.length > 0) {
          await waitForDsqlJob(db, jobId);
        } else if (isAsyncDdl(stmt)) {
          const skippedIfNotExists =
            rows.length === 0 && /\bIF\s+NOT\s+EXISTS\b/i.test(stmt);
          if (!skippedIfNotExists) {
            throw new Error(
              "Expected a job_id from an asynchronous DDL statement but none " +
                "was returned, so the background job cannot be awaited. " +
                "Refusing to record the statement as applied.",
            );
          }
        }
      } catch (e) {
        return fail(migration, stmtIdx, stmt, describeError(e));
      }

      // The statement committed (autocommit). Record it separately: a failure
      // here leaves it applied but untracked, so report it for reconciliation
      // rather than silently continuing.
      try {
        await recordStatement(migration, stmtIdx, currentStmtHash);
      } catch (e) {
        return fail(
          migration,
          stmtIdx,
          stmt,
          `Statement applied but recording it in the tracking table failed: ${describeError(e)}. ` +
            "Reconcile the tracking table before re-running.",
        );
      }
      appliedStatementsCount++;
    }

    if (migrationHadPendingStatements) {
      completedMigrations++;
    }
  }

  return {
    success: true,
    appliedStatements: appliedStatementsCount,
    totalStatements,
    completedMigrations,
    totalMigrations,
  };
}

/**
 * Report how many migrations/statements are applied vs. pending, without
 * changing the database.
 */
export async function getMigrationStatus(
  db: AnyNodePgDatabase,
  config: string | MigrationConfig,
): Promise<{
  appliedMigrations: number;
  pendingMigrations: number;
  appliedStatements: number;
  pendingStatements: number;
}> {
  return getMigrationStatusInternal(db, readMigrations(config), config);
}

/**
 * Status core, taking already-parsed migrations. Exposed for unit tests that
 * supply migrations without reading from disk.
 * @internal
 */
export async function getMigrationStatusInternal(
  db: AnyNodePgDatabase,
  migrations: MigrationMeta[],
  config: string | MigrationConfig,
): Promise<{
  appliedMigrations: number;
  pendingMigrations: number;
  appliedStatements: number;
  pendingStatements: number;
}> {
  const { migrationsTable, migrationsSchema } = resolveMigrationTarget(config);

  const tableExists = (await withOccRetry(() =>
    db.execute(sql`
    SELECT EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = ${migrationsSchema}
      AND table_name = ${migrationsTable}
    ) as exists
  `),
  )) as QueryResult<{ exists: boolean }>;

  if (!tableExists.rows[0]?.exists) {
    const totalStatements = migrations.reduce(
      (sum, m) => sum + m.sql.length,
      0,
    );
    return {
      appliedMigrations: 0,
      pendingMigrations: migrations.length,
      appliedStatements: 0,
      pendingStatements: totalStatements,
    };
  }

  const applied = (await withOccRetry(() =>
    db.execute(
      sql`SELECT migration_folder_millis, statement_index
      FROM ${sql.identifier(migrationsSchema)}.${sql.identifier(migrationsTable)}`,
    ),
  )) as QueryResult<{
    migration_folder_millis: string | number;
    statement_index: number;
  }>;

  const appliedSet = new Set(
    applied.rows.map(
      (row) => `${Number(row.migration_folder_millis)}:${row.statement_index}`,
    ),
  );

  let appliedMigrations = 0;
  let pendingMigrations = 0;
  let appliedStatements = 0;
  let pendingStatements = 0;

  for (const migration of migrations) {
    let fullyApplied = true;
    for (let stmtIdx = 0; stmtIdx < migration.sql.length; stmtIdx++) {
      if (appliedSet.has(`${migration.folderMillis}:${stmtIdx}`)) {
        appliedStatements++;
      } else {
        pendingStatements++;
        fullyApplied = false;
      }
    }
    if (fullyApplied) {
      appliedMigrations++;
    } else {
      pendingMigrations++;
    }
  }

  return {
    appliedMigrations,
    pendingMigrations,
    appliedStatements,
    pendingStatements,
  };
}
