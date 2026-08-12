import { splitSqlStatements, isMultiStatement } from "../src/sql-statements";

// Ported from the Tortoise adapter's test_sql_splitting.py so the boundary
// rules stay identical across adapters: semicolons in strings, quoted
// identifiers, comments, and dollar quotes.
describe("splitSqlStatements", () => {
  test("basic splitting", () => {
    expect(
      splitSqlStatements("CREATE TABLE a (id INT); CREATE TABLE b (id INT)"),
    ).toEqual(["CREATE TABLE a (id INT)", "CREATE TABLE b (id INT)"]);
  });

  test("semicolon in single-quoted string", () => {
    expect(
      splitSqlStatements(
        "INSERT INTO t VALUES ('a;b'); INSERT INTO t VALUES ('c')",
      ),
    ).toEqual(["INSERT INTO t VALUES ('a;b')", "INSERT INTO t VALUES ('c')"]);
  });

  test("semicolon in double-quoted identifier", () => {
    expect(
      splitSqlStatements(
        'CREATE TABLE "my;table" (id INT); CREATE TABLE other (id INT)',
      ),
    ).toEqual([
      'CREATE TABLE "my;table" (id INT)',
      "CREATE TABLE other (id INT)",
    ]);
  });

  test("escaped single quote", () => {
    expect(
      splitSqlStatements("INSERT INTO t VALUES ('it''s;here'); SELECT 1"),
    ).toEqual(["INSERT INTO t VALUES ('it''s;here')", "SELECT 1"]);
  });

  test("escaped double quote", () => {
    expect(
      splitSqlStatements('CREATE TABLE "has""semi;colon" (id INT); SELECT 1'),
    ).toEqual(['CREATE TABLE "has""semi;colon" (id INT)', "SELECT 1"]);
  });

  test("mixed quotes", () => {
    expect(
      splitSqlStatements(
        `INSERT INTO t VALUES ('he said "hi;there"'); SELECT 1`,
      ),
    ).toEqual([`INSERT INTO t VALUES ('he said "hi;there"')`, "SELECT 1"]);
  });

  test("trailing semicolon", () => {
    expect(splitSqlStatements("SELECT 1;")).toEqual(["SELECT 1"]);
  });

  test("no semicolon", () => {
    expect(splitSqlStatements("SELECT 1")).toEqual(["SELECT 1"]);
  });

  test("empty input", () => {
    expect(splitSqlStatements("")).toEqual([]);
  });

  test("only whitespace", () => {
    expect(splitSqlStatements("   ")).toEqual([]);
  });

  test("multiple consecutive semicolons", () => {
    expect(splitSqlStatements("SELECT 1;; SELECT 2")).toEqual([
      "SELECT 1",
      "SELECT 2",
    ]);
  });

  test("dollar-quoted string", () => {
    expect(
      splitSqlStatements("SELECT $$contains;semicolon$$; SELECT 1"),
    ).toEqual(["SELECT $$contains;semicolon$$", "SELECT 1"]);
  });

  test("tagged dollar-quoted string", () => {
    expect(
      splitSqlStatements("SELECT $foo$contains;semicolon$foo$; SELECT 1"),
    ).toEqual(["SELECT $foo$contains;semicolon$foo$", "SELECT 1"]);
  });

  test("mismatched dollar-quote tags split on the semicolon", () => {
    expect(splitSqlStatements("SELECT $foo$hello; world$bar$")).toEqual([
      "SELECT $foo$hello",
      "world$bar$",
    ]);
  });

  test("single quote inside dollar-quoted string", () => {
    expect(splitSqlStatements("SELECT $$it's fine$$; SELECT 1")).toEqual([
      "SELECT $$it's fine$$",
      "SELECT 1",
    ]);
  });

  test("quoted string before and inside dollar-quoted string", () => {
    expect(splitSqlStatements("SELECT 'a', $$it's; fine$$; SELECT 1")).toEqual([
      "SELECT 'a', $$it's; fine$$",
      "SELECT 1",
    ]);
  });

  test("double quote inside dollar-quoted string", () => {
    expect(
      splitSqlStatements('SELECT $$say "hello; world"$$; SELECT 1'),
    ).toEqual(['SELECT $$say "hello; world"$$', "SELECT 1"]);
  });

  test("combined stress test", () => {
    const sql = `
          CREATE TABLE "weird;name" (id INT);
          INSERT INTO t VALUES ('it''s;tricky');
          CREATE TABLE "a""b;c" (x INT); SELECT 1`;
    expect(splitSqlStatements(sql)).toEqual([
      'CREATE TABLE "weird;name" (id INT)',
      "INSERT INTO t VALUES ('it''s;tricky')",
      'CREATE TABLE "a""b;c" (x INT)',
      "SELECT 1",
    ]);
  });

  test("semicolon in single-line comment", () => {
    expect(
      splitSqlStatements("SELECT 1 -- comment with ; semicolon\n; SELECT 2"),
    ).toEqual(["SELECT 1 -- comment with ; semicolon", "SELECT 2"]);
  });

  test("semicolon in trailing multi-line comment", () => {
    expect(
      splitSqlStatements("SELECT 1 /* comment\n;\nhere */; SELECT 2"),
    ).toEqual(["SELECT 1 /* comment\n;\nhere */", "SELECT 2"]);
  });

  test("semicolon in leading multi-line comment", () => {
    expect(
      splitSqlStatements("SELECT 1; /* comment\n;\nhere */SELECT 2"),
    ).toEqual(["SELECT 1", "/* comment\n;\nhere */SELECT 2"]);
  });

  test("empty multi-line comment", () => {
    expect(splitSqlStatements("SELECT /**/1; SELECT 2")).toEqual([
      "SELECT /**/1",
      "SELECT 2",
    ]);
  });

  test("comment-like sequence in string is not a comment", () => {
    expect(
      splitSqlStatements("SELECT '-- not; comment'; SELECT '/* also; not */'"),
    ).toEqual(["SELECT '-- not; comment'", "SELECT '/* also; not */'"]);
  });

  test("arithmetic operators are not comment starts", () => {
    expect(splitSqlStatements("SELECT 5-3; SELECT 10/2")).toEqual([
      "SELECT 5-3",
      "SELECT 10/2",
    ]);
  });
});

describe("isMultiStatement", () => {
  test("single statement (with or without trailing semicolon)", () => {
    expect(isMultiStatement("CREATE TABLE a (id INT)")).toBe(false);
    expect(isMultiStatement("CREATE TABLE a (id INT);")).toBe(false);
  });

  test("a semicolon inside a string does not make it multi-statement", () => {
    expect(isMultiStatement("INSERT INTO t VALUES ('a;b')")).toBe(false);
  });

  test("two real statements", () => {
    expect(
      isMultiStatement("CREATE TABLE a (id INT); CREATE TABLE b (id INT)"),
    ).toBe(true);
  });

  test("empty / whitespace is not multi-statement", () => {
    expect(isMultiStatement("")).toBe(false);
    expect(isMultiStatement("   ")).toBe(false);
  });
});
