import { pgTable, text } from "drizzle-orm/pg-core";
import { drizzle, AwsDsqlDatabase } from "../src/driver";

describe("drizzle.mock", () => {
  test("builds a usable AwsDsqlDatabase without a live connection", () => {
    const db = drizzle.mock();
    expect(db).toBeInstanceOf(AwsDsqlDatabase);
    expect(typeof db.execute).toBe("function");
    expect(typeof db.select).toBe("function");
    expect(typeof db.transactionWithRetry).toBe("function");
  });
});

describe("drizzle() with a provided client", () => {
  test("accepts a client directly", () => {
    const client = { query: jest.fn() } as never;
    const db = drizzle(client);
    expect(db).toBeInstanceOf(AwsDsqlDatabase);
    expect(typeof db.select).toBe("function");
    expect(db.$client).toBe(client);
  });

  test("accepts a client via the config object", () => {
    const client = { query: jest.fn() } as never;
    const db = drizzle({ client });
    expect(db).toBeInstanceOf(AwsDsqlDatabase);
    expect(typeof db.select).toBe("function");
    expect(db.$client).toBe(client);
  });

  test("exposes transactionWithRetry on the returned database", () => {
    const client = { query: jest.fn() } as never;
    const db = drizzle(client);
    expect(typeof db.transactionWithRetry).toBe("function");
  });
});

describe("drizzle() two-arg client + config form", () => {
  test("resolves drizzle(client, { schema }) and surfaces the relational query API", () => {
    const users = pgTable("users", { id: text("id") });
    const client = { query: jest.fn() } as never;

    const db = drizzle(client, { schema: { users } });

    expect(db.$client).toBe(client);
    // The schema passed at construction drives db.query.<table>.
    expect(Object.keys(db.query)).toContain("users");
  });
});

describe("drizzle() connection path", () => {
  test("builds the pool via the connector, which rejects an empty host", () => {
    // The connection form reaches the Aurora DSQL connector, which demands a
    // real cluster host — an empty host surfaces as an error, confirming the
    // connection branch is wired through to the connector.
    expect(() => drizzle({ connection: { host: "", user: "role" } })).toThrow();
  });

  test("requires a user rather than defaulting to a privileged role", () => {
    // Typed as required; the cast covers JavaScript callers.
    expect(() =>
      drizzle({ connection: { host: "abc.dsql.us-east-1.on.aws" } } as never),
    ).toThrow(/connection\.user is required/);
  });
});
