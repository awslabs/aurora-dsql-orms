import { DrizzleError } from "drizzle-orm";
import { isOCCError } from "@aws/aurora-dsql-node-postgres-connector";

const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_BASE_DELAY_MS = 50;
const DEFAULT_MAX_DELAY_MS = 5000;

/**
 * Thrown when a transaction still conflicts after the configured number of
 * retries. The last underlying error is preserved as `cause`.
 */
export class AwsDsqlRetryExhaustedError extends DrizzleError {
  constructor(
    /** Total attempts made, counting the first, non-retry attempt. */
    public readonly attempts: number,
    cause: unknown,
  ) {
    super({
      message:
        `DSQL operation failed after ${attempts} attempts ` +
        `(${attempts - 1} retries) due to ` +
        "optimistic concurrency conflicts. This usually means multiple " +
        "transactions are modifying the same data. Consider increasing " +
        "maxRetries or reducing contention.",
      cause,
    });
    this.name = "AwsDsqlRetryExhaustedError";
  }
}

/** Retry behavior for {@link AwsDsqlDatabase.transactionWithRetry}. */
export interface AwsDsqlRetryConfig {
  /** Maximum number of retries after the first attempt (default: 3). */
  maxRetries?: number;
  /** Base delay in ms for exponential backoff (default: 50). */
  baseDelayMs?: number;
  /** Ceiling for the backoff delay in ms (default: 5000). */
  maxDelayMs?: number;
  /** Invoked before each retry — use for structured logging/metrics. */
  onRetry?: (error: unknown, attempt: number, maxAttempts: number) => void;
}

/**
 * Reject pathological retry configs up front so a typo can't turn into an
 * unbounded loop or a zero-delay hot loop.
 *
 * @throws {DrizzleError} when a field is out of range.
 */
export function validateRetryConfig(config: AwsDsqlRetryConfig): void {
  // `number` admits NaN, Infinity and fractions, none of which the retry loop
  // can honor: Infinity never reaches its exit branch, NaN skips the loop
  // entirely (so `fn` never runs), and a fraction never equals `attempt`, so
  // the loop falls through and drops the original error.
  if (
    config.maxRetries !== undefined &&
    (!Number.isInteger(config.maxRetries) || config.maxRetries < 0)
  ) {
    throw new DrizzleError({
      message: `Invalid retryConfig: maxRetries must be an integer >= 0, got ${config.maxRetries}`,
    });
  }
  if (
    config.baseDelayMs !== undefined &&
    (!Number.isFinite(config.baseDelayMs) || config.baseDelayMs <= 0)
  ) {
    throw new DrizzleError({
      message: `Invalid retryConfig: baseDelayMs must be a finite number > 0, got ${config.baseDelayMs}`,
    });
  }
  if (
    config.maxDelayMs !== undefined &&
    (!Number.isFinite(config.maxDelayMs) || config.maxDelayMs <= 0)
  ) {
    throw new DrizzleError({
      message: `Invalid retryConfig: maxDelayMs must be a finite number > 0, got ${config.maxDelayMs}`,
    });
  }
  if (
    config.baseDelayMs !== undefined &&
    config.maxDelayMs !== undefined &&
    config.maxDelayMs < config.baseDelayMs
  ) {
    throw new DrizzleError({
      message: `Invalid retryConfig: maxDelayMs (${config.maxDelayMs}) must be >= baseDelayMs (${config.baseDelayMs})`,
    });
  }
}

/**
 * True if `error` is (or wraps) a DSQL OCC conflict. The retryable SQLSTATEs
 * (OC000/OC001, surfaced as 40001 at COMMIT) are classified by the connector's
 * `isOCCError`, so there is a single source of truth for which codes retry.
 * Drizzle wraps driver errors in a `DrizzleQueryError` whose real code lives on
 * `cause`, so the chain is walked and each link handed to the classifier —
 * checking the top level alone misses every conflict raised inside a query.
 */
export function isDsqlRetryableError(error: unknown): boolean {
  let current: unknown = error;
  while (current != null) {
    if (isOCCError(current)) {
      return true;
    }
    if (typeof current !== "object") {
      break;
    }
    current = (current as { cause?: unknown }).cause;
  }
  return false;
}

/**
 * Run `fn`, retrying on DSQL OCC conflicts with exponential backoff and equal
 * jitter. Non-retryable errors propagate immediately; exhausting the retries
 * throws {@link AwsDsqlRetryExhaustedError}. An invalid `config` rejects with
 * {@link DrizzleError} before `fn` runs.
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  config: AwsDsqlRetryConfig = {},
): Promise<T> {
  validateRetryConfig(config);

  // `??` rather than a spread over defaults: spreading copies explicitly-
  // undefined fields, which would overwrite the default and break the loop.
  const maxRetries = config.maxRetries ?? DEFAULT_MAX_RETRIES;
  const baseDelayMs = config.baseDelayMs ?? DEFAULT_BASE_DELAY_MS;
  const maxDelayMs = config.maxDelayMs ?? DEFAULT_MAX_DELAY_MS;
  const onRetry = config.onRetry;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (!isDsqlRetryableError(error)) {
        throw error;
      }
      if (attempt === maxRetries) {
        throw new AwsDsqlRetryExhaustedError(attempt + 1, error);
      }
      onRetry?.(error, attempt + 1, maxRetries + 1);
      // Exponential backoff with equal jitter (50-100% of the term), capped at
      // maxDelayMs.
      const delay = Math.min(
        baseDelayMs * 2 ** attempt * (0.5 + Math.random() * 0.5),
        maxDelayMs,
      );
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  // Unreachable: the loop either returns or throws.
  throw new AwsDsqlRetryExhaustedError(maxRetries + 1, undefined);
}
