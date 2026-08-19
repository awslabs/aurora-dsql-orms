import crypto from "node:crypto";
import { PgDialect } from "drizzle-orm/pg-core";
import type { MigrationMeta } from "drizzle-orm/migrator";
import { migrateInternal, getMigrationStatusInternal } from "../src/migrator";

const dialect = new PgDialect();
function render(query: unknown): string {
  return dialect.sqlToQuery(query as never).sql;
}

function hashStatement(stmt: string): string {
  return crypto.createHash("sha256").update(stmt.trim()).digest("hex");
}

interface AppliedRow {
  migration_folder_millis: number;
  statement_index: number;
  statement_hash: string;
}

function makeDb(appliedRows: AppliedRow[]) {
  const executed: string[] = [];
  const execute = jest.fn(async (query: unknown) => {
    const text = render(query);
    executed.push(text);
    if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
      return { rows: appliedRows };
    }
    // Async-index execute + CALL sys.wait_for_job: job_id then succeeded=true.
    if (/CREATE\s+(UNIQUE\s+)?INDEX\s+ASYNC/i.test(text)) {
      return { rows: [{ job_id: "job-abc" }] };
    }
    if (/CALL\s+sys\.wait_for_job/i.test(text)) {
      return { rows: [{ succeeded: true }] };
    }
    return { rows: [] };
  });
  return { db: { execute } as never, executed };
}

/**
 * A db whose first statement matching `pattern` fails with a wrapped `40001`,
 * and which otherwise behaves like {@link makeDb} on an empty database.
 * `attempts()` counts how many times that site was reached.
 */
function conflictOnce(pattern: RegExp) {
  let conflicted = false;
  let attempts = 0;
  const execute = jest.fn(async (query: unknown) => {
    const text = render(query);
    if (pattern.test(text)) {
      attempts++;
      if (!conflicted) {
        conflicted = true;
        // Drizzle wraps the driver error; the DSQL code lives on `cause`.
        const wrapped = new Error("Failed query: conflict");
        (wrapped as { cause?: unknown }).cause = { code: "40001" };
        throw wrapped;
      }
    }
    if (/information_schema\.tables/i.test(text)) {
      return { rows: [{ exists: true }] };
    }
    if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
      return { rows: [] };
    }
    if (/CREATE\s+(UNIQUE\s+)?INDEX\s+ASYNC/i.test(text)) {
      return { rows: [{ job_id: "job-abc" }] };
    }
    if (/CALL\s+sys\.wait_for_job/i.test(text)) {
      return { rows: [{ succeeded: true }] };
    }
    return { rows: [] };
  });
  return { db: { execute } as never, attempts: () => attempts };
}

const MIGRATION: MigrationMeta = {
  sql: [
    `CREATE TABLE "a" ("id" UUID PRIMARY KEY)`,
    `CREATE INDEX ASYNC "a_idx" ON "a"("id")`,
  ],
  folderMillis: 1700000000000,
  hash: "hashA",
  bps: true,
};

describe("migrateInternal", () => {
  test("applies all statements on a fresh database and tracks each", async () => {
    const { db, executed } = makeDb([]);

    const result = await migrateInternal(db, [MIGRATION], "test");

    expect(result.success).toBe(true);
    expect(result.appliedStatements).toBe(2);
    expect(result.totalStatements).toBe(2);
    expect(result.completedMigrations).toBe(1);
    expect(result.totalMigrations).toBe(1);

    expect(executed.some((t) => t.includes('CREATE TABLE "a"'))).toBe(true);
    expect(executed.some((t) => t.includes('CREATE INDEX ASYNC "a_idx"'))).toBe(
      true,
    );
    // One tracking INSERT per applied statement.
    expect(executed.filter((t) => /^\s*INSERT INTO/i.test(t))).toHaveLength(2);
  });

  test("waits on sys.wait_for_job after CREATE INDEX ASYNC before recording", async () => {
    const { db, executed } = makeDb([]);
    await migrateInternal(db, [MIGRATION], "test");

    const idx = (needle: RegExp) => executed.findIndex((t) => needle.test(t));
    const createIndexIdx = idx(/CREATE\s+INDEX\s+ASYNC\s+"a_idx"/i);
    const waitIdx = idx(/sys\.wait_for_job/i);
    const trackingInserts = executed
      .map((t, i) => ({ t, i }))
      .filter(({ t }) => /^\s*INSERT INTO/i.test(t));
    const asyncTrackingInsert = trackingInserts[1]?.i ?? -1;

    // wait_for_job must run AFTER CREATE INDEX ASYNC and BEFORE the tracking
    // insert that marks that statement as applied.
    expect(createIndexIdx).toBeGreaterThanOrEqual(0);
    expect(waitIdx).toBeGreaterThan(createIndexIdx);
    expect(asyncTrackingInsert).toBeGreaterThan(waitIdx);
  });

  test("fails the migration when sys.wait_for_job reports the async job failed", async () => {
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: [] };
      }
      if (/CREATE\s+INDEX\s+ASYNC/i.test(text)) {
        return { rows: [{ job_id: "job-bad" }] };
      }
      if (/CALL\s+sys\.wait_for_job/i.test(text)) {
        return { rows: [{ succeeded: false }] };
      }
      return { rows: [] };
    });

    const migration: MigrationMeta = {
      sql: [`CREATE INDEX ASYNC "a_idx" ON "a"("id")`],
      folderMillis: 1700000000000,
      hash: "hashOnlyAsync",
      bps: true,
    };

    const result = await migrateInternal(
      { execute } as never,
      [migration],
      "test",
    );
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.message).toMatch(/async job job-bad did not succeed/);
    }
  });

  test("fails the migration when sys.wait_for_job returns an unknown status", async () => {
    // A null `succeeded` (e.g. the wait timed out before a terminal state) must
    // not be treated as success — the index build isn't confirmed.
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: [] };
      }
      if (/CREATE\s+INDEX\s+ASYNC/i.test(text)) {
        return { rows: [{ job_id: "job-slow" }] };
      }
      if (/CALL\s+sys\.wait_for_job/i.test(text)) {
        return { rows: [{ succeeded: null }] };
      }
      return { rows: [] };
    });

    const migration: MigrationMeta = {
      sql: [`CREATE INDEX ASYNC "a_idx" ON "a"("id")`],
      folderMillis: 1700000000000,
      hash: "hashOnlyAsync",
      bps: true,
    };

    const result = await migrateInternal(
      { execute } as never,
      [migration],
      "test",
    );
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.message).toMatch(
        /did not succeed \(succeeded=unknown\)/,
      );
    }
  });

  test("keys tracking on (folderMillis, statementIndex), not the migration hash", async () => {
    // Regression: the identity used to be `${migration.hash}:${idx}` which
    // rekeys every applied statement when ANY statement in the file changes.
    // If we hand the resume path a row with a DIFFERENT `migration_hash` but
    // the same `folder_millis`+`statement_index`, statement 0 must still be
    // considered applied.
    const applied: AppliedRow[] = [
      {
        migration_folder_millis: 1700000000000,
        statement_index: 0,
        statement_hash: hashStatement(MIGRATION.sql[0]!),
      },
    ];
    const { db, executed } = makeDb(applied);

    const result = await migrateInternal(db, [MIGRATION], "test");

    expect(result.success).toBe(true);
    expect(result.appliedStatements).toBe(1);
    // Statement 0 must not be re-executed; statement 1 should.
    expect(executed.some((t) => t.includes('CREATE TABLE "a"'))).toBe(false);
    expect(executed.some((t) => t.includes('CREATE INDEX ASYNC "a_idx"'))).toBe(
      true,
    );
  });

  test("warns and skips when an applied statement's hash has changed", async () => {
    const applied: AppliedRow[] = [
      {
        migration_folder_millis: 1700000000000,
        statement_index: 0,
        statement_hash: "deadbeefdeadbeef",
      },
    ];
    const { db, executed } = makeDb(applied);
    const warn = jest.spyOn(console, "warn").mockImplementation(() => {});

    await migrateInternal(db, [MIGRATION], "test");

    expect(warn).toHaveBeenCalledWith(
      expect.stringContaining("has changed since it was applied"),
    );
    expect(executed.some((t) => t.includes('CREATE TABLE "a"'))).toBe(false);
    warn.mockRestore();
  });

  test("rejects a chunk that holds multiple statements (breakpoints:false)", async () => {
    // A breakpoint-free migration lands as one chunk with several DDLs. DSQL
    // allows one DDL per transaction, so the migrator must reject it up front
    // and execute neither statement.
    const migration: MigrationMeta = {
      sql: [
        `CREATE TABLE "a" ("id" UUID PRIMARY KEY);\nCREATE TABLE "b" ("id" UUID PRIMARY KEY)`,
      ],
      folderMillis: 1700000000000,
      hash: "hashMulti",
      bps: true,
    };
    const { db, executed } = makeDb([]);

    const result = await migrateInternal(db, [migration], "test");

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.statementIndex).toBe(0);
      expect(result.error.message).toMatch(/multiple SQL statements/);
    }
    // Neither DDL is executed.
    expect(executed.some((t) => t.includes('CREATE TABLE "a"'))).toBe(false);
    expect(executed.some((t) => t.includes('CREATE TABLE "b"'))).toBe(false);
  });

  test("stops and reports details when a statement fails", async () => {
    const executed: string[] = [];
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      executed.push(text);
      if (text.includes('CREATE TABLE "a"')) {
        throw new Error("boom");
      }
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: [] };
      }
      return { rows: [] };
    });

    const result = await migrateInternal(
      { execute } as never,
      [MIGRATION],
      "test",
    );

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.statementIndex).toBe(0);
      expect(result.error.message).toBe("boom");
      expect(result.error.sql).toContain('CREATE TABLE "a"');
    }
    // Second statement never runs after the first fails.
    expect(executed.some((t) => t.includes('CREATE INDEX ASYNC "a_idx"'))).toBe(
      false,
    );
  });

  test("tracks an empty statement chunk without executing it as DDL", async () => {
    // A trailing `--> statement-breakpoint` yields an empty chunk. It must be
    // recorded (so indices stay aligned on re-run) but never sent to the db.
    const migration: MigrationMeta = {
      sql: [`CREATE TABLE "a" ("id" UUID PRIMARY KEY)`, "   "],
      folderMillis: 1700000000000,
      hash: "hashEmpty",
      bps: true,
    };
    const { db, executed } = makeDb([]);

    const result = await migrateInternal(db, [migration], "test");

    expect(result.success).toBe(true);
    expect(result.appliedStatements).toBe(2);
    expect(result.totalStatements).toBe(2);
    // Both chunks are tracked, including the empty one...
    expect(executed.filter((t) => /^\s*INSERT INTO/i.test(t))).toHaveLength(2);
    // ...but the empty chunk is never executed as a (blank) DDL statement.
    expect(executed.every((t) => t.trim() !== "")).toBe(true);
  });

  test("reports the statement as applied-but-untracked when only the tracking insert fails", async () => {
    const executed: string[] = [];
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      executed.push(text);
      // DDL succeeds; only the tracking INSERT for statement 0 fails.
      if (/^\s*INSERT INTO/i.test(text)) {
        throw new Error("insert failed");
      }
      return { rows: [] };
    });

    const result = await migrateInternal(
      { execute } as never,
      [MIGRATION],
      "test",
    );

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.statementIndex).toBe(0);
      expect(result.error.message).toContain("applied but recording");
      expect(result.error.sql).toContain('CREATE TABLE "a"');
    }
  });

  test("retries a migration statement that hits an OCC conflict, then succeeds", async () => {
    let createTableAttempts = 0;
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: [] };
      }
      if (/CREATE TABLE "a"/.test(text)) {
        createTableAttempts++;
        if (createTableAttempts === 1) {
          // Drizzle wraps the driver error; the DSQL code lives on `cause`.
          // The connector does not retry db.execute(), so the migrator must.
          const wrapped = new Error("Failed query: create table");
          (wrapped as { cause?: unknown }).cause = { code: "40001" };
          throw wrapped;
        }
      }
      if (/CREATE\s+INDEX\s+ASYNC/i.test(text)) {
        return { rows: [{ job_id: "job-abc" }] };
      }
      if (/CALL\s+sys\.wait_for_job/i.test(text)) {
        return { rows: [{ succeeded: true }] };
      }
      return { rows: [] };
    });

    const result = await migrateInternal(
      { execute } as never,
      [MIGRATION],
      "test",
    );

    expect(result.success).toBe(true);
    expect(result.appliedStatements).toBe(2);
    expect(createTableAttempts).toBe(2);
  });

  test("does not retry a non-OCC failure", async () => {
    let attempts = 0;
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: [] };
      }
      if (/CREATE TABLE "a"/.test(text)) {
        attempts++;
        throw Object.assign(new Error("syntax error"), { code: "42601" });
      }
      return { rows: [] };
    });

    const result = await migrateInternal(
      { execute } as never,
      [MIGRATION],
      "test",
    );

    expect(result.success).toBe(false);
    // A bad migration must fail on the first attempt, not after backoff.
    expect(attempts).toBe(1);
  });

  // Every db.execute call site is wrapped in withOccRetry, not just the
  // migration DDL: the connector retries its own transaction() but leaves
  // pool.query() alone, so a conflict at any of these would otherwise abort
  // the whole run. Each pattern below pins one site.
  test.each([
    ["CREATE SCHEMA", /CREATE SCHEMA IF NOT EXISTS/i],
    ["tracking CREATE TABLE", /CREATE TABLE IF NOT EXISTS/i],
    ["applied-rows SELECT", /^\s*SELECT migration_folder_millis/i],
    // The migration's own DDL, distinct from the tracking table's guarded
    // CREATE: this is the statement a busy cluster is most likely to conflict.
    ["migration DDL statement", /^\s*CREATE TABLE "a"/i],
    ["tracking INSERT", /INSERT INTO/i],
    ["sys.wait_for_job", /CALL\s+sys\.wait_for_job/i],
  ])("retries an OCC conflict at the %s site", async (_label, pattern) => {
    const { db, attempts } = conflictOnce(pattern);

    const result = await migrateInternal(db, [MIGRATION], "test");

    expect(result.success).toBe(true);
    expect(result.appliedStatements).toBe(2);
    // Two hits on the conflicting site: the rejected attempt and the retry.
    expect(attempts()).toBeGreaterThanOrEqual(2);
  });

  // AwsDsqlRetryExhaustedError's own message is generic advice; the SQLSTATE
  // sits further down the cause chain.
  test("reports the underlying SQLSTATE when retries are exhausted", async () => {
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: [] };
      }
      if (/CREATE TABLE "a"/.test(text)) {
        const wrapped = new Error("Failed query: create table");
        (wrapped as { cause?: unknown }).cause = { code: "40001" };
        throw wrapped;
      }
      return { rows: [] };
    });

    const result = await migrateInternal(
      { execute } as never,
      [MIGRATION],
      "test",
    );

    expect(result.success).toBe(false);
    if (result.success) {
      return;
    }
    expect(result.error.message).toContain("40001");
    // The generic wrapper text is kept as context, not replaced.
    expect(result.error.message).toContain("optimistic concurrency conflicts");
  });

  test("waits on the job_id returned by ALTER TABLE ASYNC ... VALIDATE CONSTRAINT", async () => {
    const validateMigration: MigrationMeta = {
      sql: [`ALTER TABLE ASYNC "a" VALIDATE CONSTRAINT "a_check"`],
      folderMillis: 1700000001000,
      hash: "hashV",
      bps: true,
    };
    const executed: string[] = [];
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      executed.push(text);
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: [] };
      }
      if (/ALTER\s+TABLE\s+ASYNC/i.test(text)) {
        return { rows: [{ job_id: "job-validate" }] };
      }
      if (/CALL\s+sys\.wait_for_job/i.test(text)) {
        return { rows: [{ succeeded: true }] };
      }
      return { rows: [] };
    });

    const result = await migrateInternal(
      { execute } as never,
      [validateMigration],
      "test",
    );

    expect(result.success).toBe(true);
    const idx = (needle: RegExp) => executed.findIndex((t) => needle.test(t));
    const alterIdx = idx(/ALTER\s+TABLE\s+ASYNC/i);
    const waitIdx = idx(/sys\.wait_for_job/i);
    const insertIdx = idx(/^\s*INSERT INTO/i);

    // Constraint validation is asynchronous just like an index build, so the
    // wait must sit between the DDL and the row marking it applied.
    expect(waitIdx).toBeGreaterThan(alterIdx);
    expect(insertIdx).toBeGreaterThan(waitIdx);
  });

  // The wait is driven by the returned job_id, not by matching the statement
  // against ASYNC_DDL_RE.
  test("waits on a job_id returned by a statement that is not async DDL", async () => {
    const plainDdl: MigrationMeta = {
      sql: [`CREATE TABLE "b" ("id" UUID PRIMARY KEY)`],
      folderMillis: 1700000002000,
      hash: "hashJ",
      bps: true,
    };
    const executed: string[] = [];
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      executed.push(text);
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: [] };
      }
      if (/CREATE TABLE "b"/.test(text)) {
        return { rows: [{ job_id: "job-plain" }] };
      }
      if (/CALL\s+sys\.wait_for_job/i.test(text)) {
        return { rows: [{ succeeded: true }] };
      }
      return { rows: [] };
    });

    const result = await migrateInternal(
      { execute } as never,
      [plainDdl],
      "test",
    );

    expect(result.success).toBe(true);
    const idx = (needle: RegExp) => executed.findIndex((t) => needle.test(t));
    const waitIdx = idx(/sys\.wait_for_job/i);
    const insertIdx = idx(/^\s*INSERT INTO/i);

    expect(waitIdx).toBeGreaterThan(-1);
    expect(insertIdx).toBeGreaterThan(waitIdx);
  });

  test("fails when an asynchronous DDL returns no job_id", async () => {
    const asyncNoJob: MigrationMeta = {
      sql: [`CREATE INDEX ASYNC "a_idx" ON "a"("id")`],
      folderMillis: 1700000002000,
      hash: "hashN",
      bps: true,
    };
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: [] };
      }
      // Async DDL that answered with a row carrying no job_id: the background
      // job can't be awaited, so it must not be recorded as applied. Note this
      // is a returned row, not an empty result — see the no-op test below.
      return { rows: [{ unexpected: "no job_id here" }] };
    });

    const result = await migrateInternal(
      { execute } as never,
      [asyncNoJob],
      "test",
    );

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.message).toContain("Expected a job_id");
    }
  });

  // Confirmed against a live cluster: DSQL skips this and returns the job_id
  // column with zero rows. Reachable on the resume path, and `dsql-lint --fix`
  // emits this form from `CREATE INDEX IF NOT EXISTS`.
  test("records a skipped IF NOT EXISTS async index that returns no rows", async () => {
    const idempotentIndex: MigrationMeta = {
      sql: [`CREATE INDEX ASYNC IF NOT EXISTS "a_idx" ON "a"("id")`],
      folderMillis: 1700000003000,
      hash: "hashI",
      bps: true,
    };
    const executed: string[] = [];
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      executed.push(text);
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: [] };
      }
      // DSQL skipped it: the job_id column comes back with no rows.
      return { rows: [] };
    });

    const result = await migrateInternal(
      { execute } as never,
      [idempotentIndex],
      "test",
    );

    expect(result.success).toBe(true);
    expect(result.appliedStatements).toBe(1);
    expect(executed.some((t) => /wait_for_job/i.test(t))).toBe(false);
    expect(executed.some((t) => /^\s*INSERT INTO/i.test(t))).toBe(true);
  });
});

describe("getMigrationStatusInternal", () => {
  function makeStatusDb(exists: boolean, appliedRows: AppliedRow[]) {
    const execute = jest.fn(async (query: unknown) => {
      const text = render(query);
      if (/information_schema\.tables/i.test(text)) {
        return { rows: [{ exists }] };
      }
      if (/^\s*SELECT\s+migration_folder_millis/i.test(text)) {
        return { rows: appliedRows };
      }
      return { rows: [] };
    });
    return { execute } as never;
  }

  // Both of this function's queries are withOccRetry-wrapped too, so a
  // conflict on a busy cluster must not turn a status check into a hard error.
  test.each([
    ["information_schema lookup", /information_schema\.tables/i],
    ["applied-rows SELECT", /^\s*SELECT\s+migration_folder_millis/i],
  ])("retries an OCC conflict at the %s site", async (_label, pattern) => {
    const { db, attempts } = conflictOnce(pattern);

    const status = await getMigrationStatusInternal(db, [MIGRATION], "test");

    expect(attempts()).toBeGreaterThanOrEqual(2);
    expect(status.pendingStatements).toBe(2);
  });

  test("reports everything pending when the tracking table is absent", async () => {
    const status = await getMigrationStatusInternal(
      makeStatusDb(false, []),
      [MIGRATION],
      "test",
    );

    expect(status).toEqual({
      appliedMigrations: 0,
      pendingMigrations: 1,
      appliedStatements: 0,
      pendingStatements: 2,
    });
  });

  test("splits applied vs pending when partially applied", async () => {
    const status = await getMigrationStatusInternal(
      makeStatusDb(true, [
        {
          migration_folder_millis: 1700000000000,
          statement_index: 0,
          statement_hash: "x",
        },
      ]),
      [MIGRATION],
      "test",
    );

    expect(status).toEqual({
      appliedMigrations: 0,
      pendingMigrations: 1,
      appliedStatements: 1,
      pendingStatements: 1,
    });
  });

  test("reports a fully-applied migration", async () => {
    const status = await getMigrationStatusInternal(
      makeStatusDb(true, [
        {
          migration_folder_millis: 1700000000000,
          statement_index: 0,
          statement_hash: "x",
        },
        {
          migration_folder_millis: 1700000000000,
          statement_index: 1,
          statement_hash: "y",
        },
      ]),
      [MIGRATION],
      "test",
    );

    expect(status).toEqual({
      appliedMigrations: 1,
      pendingMigrations: 0,
      appliedStatements: 2,
      pendingStatements: 0,
    });
  });
});
