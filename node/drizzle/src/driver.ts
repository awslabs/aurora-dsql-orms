import type { Pool, PoolConfig } from "pg";
import {
  AuroraDSQLPool,
  type Logger as ConnectorLogger,
} from "@aws/aurora-dsql-node-postgres-connector";
import {
  createTableRelationsHelpers,
  DrizzleError,
  extractTablesRelationalConfig,
  type DrizzleConfig,
  type ExtractTablesWithRelations,
  type RelationalSchemaConfig,
} from "drizzle-orm";
import { DefaultLogger, type Logger } from "drizzle-orm/logger";
import { PgDatabase, PgDialect } from "drizzle-orm/pg-core";
import type {
  NodePgClient,
  NodePgQueryResultHKT,
} from "drizzle-orm/node-postgres";
import type { PgTransactionConfig } from "drizzle-orm/pg-core";
import type { AwsDsqlRetryConfig } from "./retry";
import { AwsDsqlSession, AwsDsqlTransaction } from "./session";

/** Any node-postgres client the underlying Drizzle driver accepts. */
export type AwsDsqlClient = NodePgClient;

/**
 * DSQL-specific connection options for IAM authentication, handled by the
 * Aurora DSQL connector.
 */
export interface AwsDsqlOptions {
  /** DSQL cluster hostname (e.g. "abc123.dsql.us-east-1.on.aws"). */
  host: string;
  /** Database role to connect as; scope it to what the application needs. */
  user: string;
  /** AWS region (auto-detected from the hostname if not provided). */
  region?: string;
  /** IAM profile name for credentials (defaults to the AWS provider chain). */
  profile?: string;
  /** Auth token expiration in seconds. */
  tokenDurationSecs?: number;
  /** Logger for connector-level messages (token refresh, IAM errors). */
  logger?: ConnectorLogger;
}

/**
 * Full DSQL connection configuration: DSQL-specific options plus node-postgres
 * `Pool` options. `password` and `ssl` are excluded because the connector
 * manages IAM authentication and TLS.
 *
 * @see https://node-postgres.com/apis/pool
 */
export type AwsDsqlConnectionConfig = AwsDsqlOptions &
  Omit<PoolConfig, "password" | "ssl">;

/**
 * A Drizzle database backed by Amazon Aurora DSQL.
 *
 * Adds {@link transactionWithRetry} for DSQL's optimistic-concurrency retries.
 * Nested transactions throw a clear error rather than silently committing the
 * outer one; everything else — query building, relational queries,
 * `db.transaction`, `db.execute` — is inherited from Drizzle's node-postgres
 * database.
 */
export class AwsDsqlDatabase<
  TSchema extends Record<string, unknown> = Record<string, never>,
> extends PgDatabase<
  NodePgQueryResultHKT,
  TSchema,
  ExtractTablesWithRelations<TSchema>
> {
  /**
   * Run a transaction with automatic retry on Aurora DSQL optimistic-
   * concurrency conflicts (OC000/OC001, surfaced as SQLSTATE 40001 at COMMIT).
   *
   * The callback is re-run on each retry, so it must be idempotent — no side
   * effects (email, queue writes) that must not repeat.
   *
   * @example
   * ```ts
   * await db.transactionWithRetry(async (tx) => {
   *   await tx.update(accounts).set({ balance: sql`balance - 100` }).where(...);
   *   await tx.update(accounts).set({ balance: sql`balance + 100` }).where(...);
   * });
   *
   * // with per-call retry overrides
   * await db.transactionWithRetry(
   *   async (tx) => { await tx.insert(orders).values({ ... }); },
   *   undefined,
   *   { maxRetries: 5 },
   * );
   * ```
   */
  transactionWithRetry<T>(
    transaction: (
      tx: AwsDsqlTransaction<TSchema, ExtractTablesWithRelations<TSchema>>,
    ) => Promise<T>,
    config?: PgTransactionConfig,
    retryConfig?: AwsDsqlRetryConfig,
  ): Promise<T> {
    return (
      this._.session as unknown as AwsDsqlSession<
        TSchema,
        ExtractTablesWithRelations<TSchema>
      >
    ).transactionWithRetry(transaction, config, retryConfig);
  }
}

function construct<
  TSchema extends Record<string, unknown> = Record<string, never>,
  TClient extends AwsDsqlClient = AwsDsqlClient,
>(
  client: TClient,
  config: DrizzleConfig<TSchema> = {},
): AwsDsqlDatabase<TSchema> & {
  $client: AwsDsqlClient extends TClient ? Pool : TClient;
} {
  // Under exactOptionalPropertyTypes, PgDialect/session opts don't accept an
  // explicit `undefined` — spread only fields that are actually set.
  const dialect = new PgDialect(
    config.casing !== undefined ? { casing: config.casing } : {},
  );

  let logger: Logger | undefined;
  if (config.logger === true) {
    logger = new DefaultLogger();
  } else if (config.logger !== false) {
    logger = config.logger;
  }
  const sessionOptions = {
    ...(logger !== undefined ? { logger } : {}),
    ...(config.cache !== undefined ? { cache: config.cache } : {}),
  };

  let schema:
    | RelationalSchemaConfig<
        ExtractTablesWithRelations<Record<string, unknown>>
      >
    | undefined;
  if (config.schema) {
    const tablesConfig = extractTablesRelationalConfig(
      config.schema,
      createTableRelationsHelpers,
    );
    schema = {
      fullSchema: config.schema,
      schema: tablesConfig.tables,
      tableNamesMap: tablesConfig.tableNamesMap,
    };
  }

  const session = new AwsDsqlSession(client, dialect, schema, sessionOptions);
  const db = new AwsDsqlDatabase(
    dialect,
    session,
    schema as never,
  ) as AwsDsqlDatabase<TSchema>;
  (db as unknown as { $client: unknown }).$client = client;
  (db as unknown as { $cache: unknown }).$cache = config.cache;
  return db as AwsDsqlDatabase<TSchema> & {
    $client: AwsDsqlClient extends TClient ? Pool : TClient;
  };
}

function createDsqlClient(config: AwsDsqlConnectionConfig): AwsDsqlClient {
  // Not defaulted: a default would grant callers who omit it whatever that
  // role can do. Typed as required, so this guard is for JavaScript callers.
  if (!config.user) {
    throw new DrizzleError({
      message:
        "connection.user is required: connect as a database role scoped to " +
        "what your application needs. See https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html",
    });
  }
  // Drizzle's node-postgres session already passes temporal/array values
  // through as raw strings (per-query `types`), so no pool-level type parser
  // is needed here — Drizzle's own column mappers drive the conversion.
  return new AuroraDSQLPool({
    ...config,
    application_name: config.application_name ?? "drizzle",
  });
}

/**
 * Create a Drizzle database backed by Amazon Aurora DSQL.
 *
 * Rides on `drizzle-orm/node-postgres`: the Aurora DSQL connector is a
 * `pg.Pool` with IAM token auth, so no custom dialect or session is needed.
 * Pass a `connection` for the adapter to build the pool, or bring your own
 * `client` (e.g. a preconfigured `AuroraDSQLPool`).
 *
 * @example
 * ```ts
 * import { drizzle } from "@aws/aurora-dsql-drizzle";
 *
 * const db = drizzle({
 *   connection: {
 *     host: process.env.CLUSTER_ENDPOINT!,
 *     user: "myuser",
 *     region: "us-east-1",
 *   },
 *   schema,
 * });
 * ```
 */
export function drizzle<
  TSchema extends Record<string, unknown> = Record<string, never>,
  TClient extends AwsDsqlClient = Pool,
>(
  ...params:
    | [TClient]
    | [TClient, DrizzleConfig<TSchema>]
    | [
        DrizzleConfig<TSchema> &
          ({ client: TClient } | { connection: AwsDsqlConnectionConfig }),
      ]
): AwsDsqlDatabase<TSchema> & {
  $client: AwsDsqlClient extends TClient ? Pool : TClient;
} {
  // A config object (never a live client, which exposes `query`).
  if (
    typeof params[0] === "object" &&
    params[0] !== null &&
    !("query" in params[0])
  ) {
    const config = params[0] as DrizzleConfig<TSchema> & {
      connection?: AwsDsqlConnectionConfig;
      client?: TClient;
    };

    if (config.connection) {
      const { connection, ...drizzleConfig } = config;
      const client = createDsqlClient(connection);
      return construct(client as TClient, drizzleConfig);
    }

    if (config.client) {
      const { client, ...drizzleConfig } = config;
      return construct(client, drizzleConfig);
    }
  }

  // A client was passed directly.
  const client = params[0] as TClient;
  const cfg = params[1] as DrizzleConfig<TSchema> | undefined;
  return construct(client, cfg ?? {});
}

export namespace drizzle {
  export function mock<
    TSchema extends Record<string, unknown> = Record<string, never>,
  >(
    config?: DrizzleConfig<TSchema>,
  ): AwsDsqlDatabase<TSchema> & {
    $client: "$client is not available on drizzle.mock()";
  } {
    return construct({} as AwsDsqlClient, config ?? {}) as never;
  }
}
