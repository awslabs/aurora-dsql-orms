import type { VeterinaryDb } from "../src/dsql-client";
import { pet } from "../src/schema";
import { VeterinaryService } from "../src/veterinary-service";

describe("VeterinaryService", () => {
  test("createPet uses transaction retry handling", async () => {
    const created = { id: "pet-id" };
    const returning = jest.fn().mockResolvedValue([created]);
    const values = jest.fn().mockReturnValue({ returning });
    const insert = jest.fn().mockReturnValue({ values });
    const transactionWithRetry = jest.fn(async (callback) =>
      callback({ insert }),
    );
    const db = {
      insert: jest.fn(() => {
        throw new Error("createPet bypassed transactionWithRetry");
      }),
      transactionWithRetry,
    } as unknown as VeterinaryDb;

    const service = new VeterinaryService(db);
    await expect(
      service.createPet(
        "Buddy",
        new Date("2020-01-15"),
        "00000000-0000-4000-8000-000000000001",
      ),
    ).resolves.toBe(created);

    expect(transactionWithRetry).toHaveBeenCalledTimes(1);
    expect(insert).toHaveBeenCalledWith(pet);
  });
});
