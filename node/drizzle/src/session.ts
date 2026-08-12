import { Pool, type PoolClient } from "pg";
import { DrizzleError, sql, type SQL } from "drizzle-orm";
import type {
  RelationalSchemaConfig,
  TablesRelationalConfig,
} from "drizzle-orm";
import { PgDialect, type PgTransactionConfig } from "drizzle-orm/pg-core";
import {
  NodePgSession,
  NodePgTransaction,
  type NodePgClient,
  type NodePgSessionOptions,
} from "drizzle-orm/node-postgres";
import {
  type AwsDsqlRetryConfig,
  validateRetryConfig,
  withRetry,
} from "./retry";

/**
 * Build the trailing clause of a `BEGIN` for a Drizzle `PgTransactionConfig`
 * (e.g. `isolation level serializable read only`). Mirrors what the built-in
 * node-postgres transaction emits; kept here because the base helper is
 * internal-only and not part of Drizzle's public API.
 */
function buildTransactionConfigSQL(
  config: PgTransactionConfig | undefined,
): SQL | undefined {
  if (!config) {
    return undefined;
  }
  const chunks: string[] = [];
  if (config.isolationLevel) {
    chunks.push(`isolation level ${config.isolationLevel}`);
  }
  if (config.accessMode) {
    chunks.push(config.accessMode);
  }
  if (typeof config.deferrable === "boolean") {
    chunks.push(config.deferrable ? "deferrable" : "not deferrable");
  }
  return chunks.length ? sql.raw(chunks.join(" ")) : undefined;
}

/**
 * A node-postgres session that runs transactions through `AwsDsqlTransaction`
 * (so nested transactions are rejected cleanly) and adds
 * {@link transactionWithRetry} for Aurora DSQL optimistic-concurrency retries.
 *
 * Only transaction handling is overridden; query preparation, the temporal/
 * array type parsing, and result mapping are inherited from `NodePgSession`.
 */
export class AwsDsqlSession<
  TFullSchema extends Record<string, unknown>,
  TSchema extends TablesRelationalConfig,
> extends NodePgSession<TFullSchema, TSchema> {
  private readonly dsqlClient: NodePgClient;
  private readonly dsqlSchema: RelationalSchemaConfig<TSchema> | undefined;
  private readonly dsqlOptions: NodePgSessionOptions;

  constructor(
    client: NodePgClient,
    dialect: PgDialect,
    schema: RelationalSchemaConfig<TSchema> | undefined,
    options: NodePgSessionOptions = {},
  ) {
    super(client, dialect, schema, options);
    this.dsqlClient = client;
    this.dsqlSchema = schema;
    this.dsqlOptions = options;
  }

  /**
   * Run a transaction. Reproduces the node-postgres BEGIN/COMMIT/ROLLBACK
   * flow (a dedicated pooled client per transaction) but hands the callback an
   * {@link AwsDsqlTransaction} instead of the stock transaction.
   */
  override async transaction<T>(
    transaction: (tx: AwsDsqlTransaction<TFullSchema, TSchema>) => Promise<T>,
    config?: PgTransactionConfig,
  ): Promise<T> {
    const isPool =
      this.dsqlClient instanceof Pool ||
      Object.getPrototypeOf(this.dsqlClient).constructor.name.includes("Pool");

    const session = isPool
      ? new AwsDsqlSession<TFullSchema, TSchema>(
          await (this.dsqlClient as Pool).connect(),
          this.dialect,
          this.dsqlSchema,
          this.dsqlOptions,
        )
      : this;

    const tx = new AwsDsqlTransaction<TFullSchema, TSchema>(
      this.dialect,
      session,
      this.dsqlSchema,
    );

    const configSql = buildTransactionConfigSQL(config);
    // `BEGIN` runs inside the try so a failure there still reaches the
    // `finally` and releases the client checked out above — otherwise every
    // failed BEGIN would leak a pool slot until the pool is exhausted.
    // Mirrors the connector's own AuroraDSQLPool.transaction(). The connector
    // logs rollback/release failures when a logger is configured; with none,
    // it is silent here too.
    let destroyClient = false;
    try {
      await tx.execute(configSql ? sql`begin ${configSql}` : sql`begin`);
      try {
        const result = await transaction(tx);
        await tx.execute(sql`commit`);
        return result;
      } catch (error) {
        try {
          await tx.execute(sql`rollback`);
        } catch {
          // The rollback failed, so this connection may still hold an aborted
          // transaction: destroy it instead of handing it back to the pool.
          // The original error is what the caller needs, so the rollback
          // failure is deliberately not rethrown (it would mask the cause).
          destroyClient = true;
        }
        throw error;
      }
    } finally {
      if (isPool) {
        try {
          (session.dsqlClient as PoolClient).release(destroyClient);
        } catch {
          // release() only throws when called twice; swallowing keeps the
          // original error propagating rather than replacing it here.
        }
      }
    }
  }

  /**
   * Run a transaction with automatic retry on Aurora DSQL optimistic-
   * concurrency conflicts (OC000/OC001, surfaced as SQLSTATE 40001 at COMMIT).
   *
   * The whole callback is re-run on each retry, so it must be idempotent — no
   * side effects (email, queue writes) that must not repeat.
   *
   * @param transaction The (idempotent) transaction callback.
   * @param config Optional transaction config (isolation level, access mode).
   * @param retryConfig Optional retry overrides (defaults: maxRetries=3,
   *   baseDelayMs=50, maxDelayMs=5000).
   */
  transactionWithRetry<T>(
    transaction: (tx: AwsDsqlTransaction<TFullSchema, TSchema>) => Promise<T>,
    config?: PgTransactionConfig,
    retryConfig?: AwsDsqlRetryConfig,
  ): Promise<T> {
    const resolvedRetryConfig = retryConfig ?? {};
    validateRetryConfig(resolvedRetryConfig);
    return withRetry(
      () => this.transaction(transaction, config),
      resolvedRetryConfig,
    );
  }
}

/**
 * A node-postgres transaction that rejects nesting. Aurora DSQL has no
 * savepoints, so a nested `tx.transaction()` cannot work; failing fast with a
 * clear message beats a cryptic server-side savepoint error.
 */
export class AwsDsqlTransaction<
  TFullSchema extends Record<string, unknown>,
  TSchema extends TablesRelationalConfig,
> extends NodePgTransaction<TFullSchema, TSchema> {
  override transaction<T>(
    _transaction: (tx: AwsDsqlTransaction<TFullSchema, TSchema>) => Promise<T>,
  ): Promise<T> {
    throw new DrizzleError({
      message:
        "This adapter keeps transactions flat: a nested db.transaction() is " +
        "rejected rather than silently committing the outer transaction. " +
        "Restructure your code to use a single transaction.",
    });
  }
}
