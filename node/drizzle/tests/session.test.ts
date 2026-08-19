import type { QueryResult, QueryResultRow } from "pg";
import { drizzle } from "../src/driver";
import { AwsDsqlDatabase } from "../src/driver";
import { AwsDsqlTransaction } from "../src/session";
import { AwsDsqlRetryExhaustedError } from "../src/retry";

// A minimal pg-shaped client whose `query` returns whatever the test tells it
// to. Not a Pool — the session's transaction() takes the single-client branch
// (no connect()/release()), which keeps this suite hermetic.
function makeClient(
  queryImpl: (text: string) => Promise<QueryResult<QueryResultRow>>,
) {
  const query = jest.fn(
    async (
      config: string | { text: string; name?: string },
      _params?: unknown[],
    ) => {
      const text = typeof config === "string" ? config : config.text;
      return queryImpl(text);
    },
  );
  return {
    client: { query } as never,
    query,
  };
}

function ok(rows: QueryResultRow[] = []): QueryResult<QueryResultRow> {
  return {
    rows,
    rowCount: rows.length,
    command: "",
    oid: 0,
    fields: [],
  };
}

// A pool-shaped stub that records every checkout and release. The class name
// ends in "Pool" so the session's duck-typed isPool check takes the pooled
// branch (connect() per transaction, release() in the finally) without
// needing a real pg.Pool.
class FakePool {
  readonly releases: Array<boolean | undefined> = [];
  connects = 0;

  constructor(
    private readonly queryImpl: (
      text: string,
    ) => Promise<QueryResult<QueryResultRow>>,
  ) {}

  async connect() {
    this.connects++;
    return {
      query: async (config: string | { text: string }) =>
        this.queryImpl(typeof config === "string" ? config : config.text),
      release: (destroy?: boolean) => {
        this.releases.push(destroy);
      },
    };
  }
}

describe("AwsDsqlDatabase.transaction", () => {
  test("wraps the callback in BEGIN/COMMIT and hands it an AwsDsqlTransaction", async () => {
    const seen: string[] = [];
    const { client } = makeClient(async (text) => {
      seen.push(text.trim().toLowerCase());
      return ok();
    });
    const db = drizzle(client);

    const result = await db.transaction(async (tx) => {
      expect(tx).toBeInstanceOf(AwsDsqlTransaction);
      // A real Drizzle transaction exposes the query-builder surface.
      expect(typeof (tx as { select: unknown }).select).toBe("function");
      return "ok";
    });

    expect(result).toBe("ok");
    expect(seen[0]).toBe("begin");
    expect(seen[seen.length - 1]).toBe("commit");
  });

  test("issues ROLLBACK and rethrows on error", async () => {
    const seen: string[] = [];
    const { client } = makeClient(async (text) => {
      seen.push(text.trim().toLowerCase());
      return ok();
    });
    const db = drizzle(client);

    await expect(
      db.transaction(async () => {
        throw new Error("callback boom");
      }),
    ).rejects.toThrow("callback boom");

    expect(seen[0]).toBe("begin");
    expect(seen).toContain("rollback");
    expect(seen).not.toContain("commit");
  });

  // DSQL raises conflicts at COMMIT, so a failure there is the common case
  // rather than an exotic one. A non-retryable COMMIT error must still roll
  // back and surface unchanged, without the retry loop being involved.
  test("rolls back and rethrows when COMMIT itself fails", async () => {
    const seen: string[] = [];
    const { client } = makeClient(async (text) => {
      const t = text.trim().toLowerCase();
      seen.push(t);
      if (t === "commit") {
        throw Object.assign(new Error("connection reset"), { code: "08006" });
      }
      return ok();
    });
    const db = drizzle(client);

    await expect(db.transaction(async () => "value")).rejects.toThrow(
      /commit/i,
    );

    expect(seen[0]).toBe("begin");
    expect(seen).toContain("rollback");
  });

  test("releases the pooled client when BEGIN itself fails", async () => {
    const pool = new FakePool(async (text) => {
      if (/^\s*begin/i.test(text)) {
        throw Object.assign(new Error("connection reset"), { code: "08006" });
      }
      return ok();
    });
    const db = drizzle(pool as never);

    await expect(db.transaction(async () => "unreachable")).rejects.toThrow(
      /begin/i,
    );

    // Without the release the pool would lose a slot on every failed BEGIN
    // until it is exhausted and every later transaction() hangs on connect().
    expect(pool.connects).toBe(1);
    expect(pool.releases).toHaveLength(1);
  });

  test("preserves the original error and destroys the client when ROLLBACK fails", async () => {
    const pool = new FakePool(async (text) => {
      if (/^\s*rollback/i.test(text)) {
        throw new Error("rollback failed: connection already gone");
      }
      return ok();
    });
    const db = drizzle(pool as never);

    await expect(
      db.transaction(async () => {
        throw new Error("original business error");
      }),
      // The caller must see the cause, not the rollback failure that followed.
    ).rejects.toThrow("original business error");

    // A connection whose ROLLBACK failed may still hold an aborted
    // transaction, so it must be destroyed rather than pooled.
    expect(pool.releases).toEqual([true]);
  });

  test("returns the client to the pool on a clean commit", async () => {
    const pool = new FakePool(async () => ok());
    const db = drizzle(pool as never);

    await expect(db.transaction(async () => "ok")).resolves.toBe("ok");

    expect(pool.releases).toEqual([false]);
  });

  test("rejects nested transactions with a clear message", async () => {
    const { client } = makeClient(async () => ok());
    const db = drizzle(client);

    await expect(
      db.transaction(async (tx) => {
        // Nesting must throw synchronously (no savepoint round-trip).
        await tx.transaction(async () => "unreachable");
      }),
    ).rejects.toThrow(/keeps transactions flat/);
  });
});

describe("AwsDsqlDatabase.transactionWithRetry", () => {
  test("retries when a wrapped 40001 is thrown at COMMIT, then commits", async () => {
    let commitCalls = 0;
    const { client } = makeClient(async (text) => {
      const t = text.trim().toLowerCase();
      if (t === "commit") {
        commitCalls++;
        if (commitCalls === 1) {
          // Simulate Drizzle wrapping the pg error.
          const wrapped = new Error("Failed query: commit");
          (wrapped as { cause?: unknown }).cause = { code: "40001" };
          throw wrapped;
        }
      }
      return ok();
    });
    const db = drizzle(client);

    let callbackCalls = 0;
    const result = await db.transactionWithRetry(
      async () => {
        callbackCalls++;
        return "done";
      },
      undefined,
      { baseDelayMs: 1, maxDelayMs: 2 },
    );

    expect(result).toBe("done");
    expect(callbackCalls).toBe(2);
    expect(commitCalls).toBe(2);
  });

  test("throws AwsDsqlRetryExhaustedError after exhausting retries", async () => {
    const { client } = makeClient(async (text) => {
      if (text.trim().toLowerCase() === "commit") {
        const wrapped = new Error("Failed query: commit");
        (wrapped as { cause?: unknown }).cause = { code: "40001" };
        throw wrapped;
      }
      return ok();
    });
    const db = drizzle(client);

    await expect(
      db.transactionWithRetry(async () => "unreachable", undefined, {
        maxRetries: 1,
        baseDelayMs: 1,
        maxDelayMs: 2,
      }),
    ).rejects.toBeInstanceOf(AwsDsqlRetryExhaustedError);
  });

  test("does not retry on non-OCC errors", async () => {
    let commitCalls = 0;
    const { client } = makeClient(async (text) => {
      if (text.trim().toLowerCase() === "commit") {
        commitCalls++;
        throw Object.assign(new Error("unique violation"), { code: "23505" });
      }
      return ok();
    });
    const db = drizzle(client);

    // Drizzle wraps driver errors in DrizzleQueryError; the pg error is on
    // `.cause`. The point is that the retry loop must NOT fire.
    let caught: unknown;
    try {
      await db.transactionWithRetry(async () => "x", undefined, {
        maxRetries: 3,
        baseDelayMs: 1,
        maxDelayMs: 2,
      });
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeDefined();
    expect(caught).not.toBeInstanceOf(AwsDsqlRetryExhaustedError);
    expect((caught as { cause?: { code?: string } })?.cause?.code).toBe(
      "23505",
    );
    expect(commitCalls).toBe(1);
  });

  test("validates the retryConfig up front", () => {
    const db = drizzle({ query: jest.fn() } as never) as AwsDsqlDatabase;
    // maxRetries < 0 must throw before the callback ever runs.
    const call = () =>
      db.transactionWithRetry(async () => "x", undefined, { maxRetries: -1 });
    expect(call).toThrow(/maxRetries must be an integer >= 0/);
  });
});
