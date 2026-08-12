import { DrizzleError } from "drizzle-orm";
import {
  type AwsDsqlRetryConfig,
  AwsDsqlRetryExhaustedError,
  isDsqlRetryableError,
  validateRetryConfig,
  withRetry,
} from "../src/retry";

describe("isDsqlRetryableError", () => {
  test("matches DSQL OCC SQLSTATE codes at the top level", () => {
    expect(isDsqlRetryableError({ code: "OC000" })).toBe(true);
    expect(isDsqlRetryableError({ code: "OC001" })).toBe(true);
    expect(isDsqlRetryableError({ code: "40001" })).toBe(true);
  });

  test("recursively unwraps DrizzleQueryError-style wrappers", () => {
    // The real bug: Drizzle wraps pg errors so the SQLSTATE lives on
    // `error.cause.code`. A top-level-only check misses every OCC conflict.
    const wrapped = new Error("Failed query: commit");
    (wrapped as { cause?: unknown }).cause = { code: "40001" };
    expect(isDsqlRetryableError(wrapped)).toBe(true);

    // Doubly-wrapped: still matches.
    const outer = new Error("outer");
    (outer as { cause?: unknown }).cause = wrapped;
    expect(isDsqlRetryableError(outer)).toBe(true);
  });

  test("ignores unrelated errors", () => {
    expect(isDsqlRetryableError({ code: "23505" })).toBe(false);
    expect(isDsqlRetryableError(new Error("nope"))).toBe(false);
    expect(isDsqlRetryableError(null)).toBe(false);
    expect(isDsqlRetryableError(undefined)).toBe(false);
    expect(isDsqlRetryableError("string")).toBe(false);
  });
});

describe("validateRetryConfig", () => {
  test("accepts defaults and valid overrides", () => {
    expect(() => validateRetryConfig({})).not.toThrow();
    expect(() =>
      validateRetryConfig({
        maxRetries: 5,
        baseDelayMs: 10,
        maxDelayMs: 1000,
      }),
    ).not.toThrow();
    expect(() => validateRetryConfig({ maxRetries: 0 })).not.toThrow();
  });

  test("rejects out-of-range fields", () => {
    expect(() => validateRetryConfig({ maxRetries: -1 })).toThrow(
      /maxRetries must be an integer >= 0/,
    );
    expect(() => validateRetryConfig({ baseDelayMs: 0 })).toThrow(
      /baseDelayMs must be a finite number > 0/,
    );
    expect(() => validateRetryConfig({ maxDelayMs: 0 })).toThrow(
      /maxDelayMs must be a finite number > 0/,
    );
    expect(() =>
      validateRetryConfig({ baseDelayMs: 100, maxDelayMs: 50 }),
    ).toThrow(/must be >= baseDelayMs/);
  });

  // All three pass the type checker; see validateRetryConfig for how each one
  // breaks the loop.
  test("rejects non-integer and non-finite values", () => {
    for (const maxRetries of [2.5, NaN, Infinity]) {
      expect(() => validateRetryConfig({ maxRetries })).toThrow(
        /maxRetries must be an integer >= 0/,
      );
    }
    for (const baseDelayMs of [NaN, Infinity]) {
      expect(() => validateRetryConfig({ baseDelayMs })).toThrow(
        /baseDelayMs must be a finite number > 0/,
      );
    }
    for (const maxDelayMs of [NaN, Infinity]) {
      expect(() => validateRetryConfig({ maxDelayMs })).toThrow(
        /maxDelayMs must be a finite number > 0/,
      );
    }
  });
});

describe("withRetry", () => {
  test("returns the first successful result without retry", async () => {
    const fn = jest.fn(async () => "ok");
    const result = await withRetry(fn);
    expect(result).toBe("ok");
    expect(fn).toHaveBeenCalledTimes(1);
  });

  test("retries wrapped-40001 errors, then succeeds", async () => {
    const wrapped = new Error("Failed query: commit");
    (wrapped as { cause?: unknown }).cause = { code: "40001" };

    const fn = jest
      .fn<Promise<string>, []>()
      .mockRejectedValueOnce(wrapped)
      .mockRejectedValueOnce(wrapped)
      .mockResolvedValueOnce("ok");

    const result = await withRetry(fn, { baseDelayMs: 1, maxDelayMs: 2 });
    expect(result).toBe("ok");
    expect(fn).toHaveBeenCalledTimes(3);
  });

  test("throws non-retryable errors immediately", async () => {
    const fn = jest.fn(async () => {
      throw new Error("not retryable");
    });
    await expect(withRetry(fn)).rejects.toThrow("not retryable");
    expect(fn).toHaveBeenCalledTimes(1);
  });

  test("throws AwsDsqlRetryExhaustedError after maxRetries", async () => {
    const fn = jest.fn(async () => {
      throw { code: "OC001" };
    });
    await expect(
      withRetry(fn, { maxRetries: 2, baseDelayMs: 1, maxDelayMs: 2 }),
    ).rejects.toBeInstanceOf(AwsDsqlRetryExhaustedError);
    expect(fn).toHaveBeenCalledTimes(3); // initial + 2 retries
  });

  test("preserves the last error as `cause` on exhaustion", async () => {
    const lastError = { code: "OC000", detail: "final" };
    const fn = jest.fn(async () => {
      throw lastError;
    });
    let caught: unknown;
    try {
      await withRetry(fn, { maxRetries: 1, baseDelayMs: 1, maxDelayMs: 2 });
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(AwsDsqlRetryExhaustedError);
    expect((caught as AwsDsqlRetryExhaustedError).attempts).toBe(2);
    expect((caught as AwsDsqlRetryExhaustedError).cause).toBe(lastError);
  });

  test("invokes onRetry with (error, attempt, maxAttempts) before each retry", async () => {
    const err = { code: "OC001" };
    const onRetry = jest.fn();
    const fn = jest
      .fn<Promise<string>, []>()
      .mockRejectedValueOnce(err)
      .mockResolvedValueOnce("ok");

    await withRetry(fn, {
      maxRetries: 2,
      baseDelayMs: 1,
      maxDelayMs: 2,
      onRetry,
    });

    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(onRetry).toHaveBeenCalledWith(err, 1, 3);
  });

  test("rejects an invalid config without invoking the callback", async () => {
    const fn = jest.fn(async () => "ok");
    await expect(withRetry(fn, { maxRetries: -1 })).rejects.toThrow(
      /maxRetries must be an integer >= 0/,
    );
    expect(fn).not.toHaveBeenCalled();
  });

  // Only reachable for consumers: exactOptionalPropertyTypes rejects this in
  // our own tree but is off by default downstream, and `{ maxRetries: opts.x }`
  // with an unset `x` is ordinary. Spreading over the defaults used to copy the
  // undefined, leaving no loop bound, so `fn` never ran.
  test("treats an explicitly-undefined field as absent", async () => {
    const fn = jest.fn(async () => "ok");
    const config = { maxRetries: undefined } as unknown as AwsDsqlRetryConfig;
    await expect(withRetry(fn, config)).resolves.toBe("ok");
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe("AwsDsqlRetryExhaustedError", () => {
  test("extends DrizzleError and carries attempts + cause", () => {
    const cause = { code: "40001" };
    const err = new AwsDsqlRetryExhaustedError(4, cause);
    expect(err).toBeInstanceOf(DrizzleError);
    expect(err.attempts).toBe(4);
    expect(err.cause).toBe(cause);
    expect(err.name).toBe("AwsDsqlRetryExhaustedError");
  });
});
