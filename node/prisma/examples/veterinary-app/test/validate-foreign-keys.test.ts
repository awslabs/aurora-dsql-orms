import { validateForeignKeys } from "../src/validate-foreign-keys";

describe("foreign key validation", () => {
  test("waits for every unvalidated constraint", async () => {
    const pool = {
      query: jest.fn(async (sql: string) => {
        if (sql.includes("FROM pg_constraint")) {
          return { rows: [{ convalidated: false }] };
        }
        if (sql.includes("ALTER TABLE ASYNC")) {
          return { rows: [{ job_id: "job-123" }] };
        }
        return { rows: [{ succeeded: true }] };
      }),
    };

    await validateForeignKeys(pool);

    expect(
      pool.query.mock.calls.filter(([sql]) =>
        String(sql).includes("CALL sys.wait_for_job"),
      ),
    ).toHaveLength(3);
    expect(
      pool.query.mock.calls
        .filter(([sql]) => String(sql).includes("FROM pg_constraint"))
        .map(([, params]) => params),
    ).toEqual([
      ["pet_ownerId_fkey", "pet"],
      ["_SpecialtyToVet_A_fkey", "_SpecialtyToVet"],
      ["_SpecialtyToVet_B_fkey", "_SpecialtyToVet"],
    ]);
    expect(
      pool.query.mock.calls
        .filter(([sql]) => String(sql).includes("FROM pg_constraint"))
        .every(([sql]) => !String(sql).includes("::regclass")),
    ).toBe(true);
  });

  test("fails when a constraint is missing", async () => {
    const pool = {
      query: jest.fn().mockResolvedValue({ rows: [] }),
    };

    await expect(validateForeignKeys(pool)).rejects.toThrow(
      "run Prisma migrations first",
    );
  });
});
