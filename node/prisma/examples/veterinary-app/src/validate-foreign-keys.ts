import { AuroraDSQLPool } from "@aws/aurora-dsql-node-postgres-connector";
import { getRequiredEnv } from "./utils";

interface QueryResult {
  rows: Record<string, unknown>[];
}

export interface QueryPool {
  query(sql: string, params?: unknown[]): Promise<QueryResult>;
}

const FOREIGN_KEYS = [
  { table: "pet", name: "pet_ownerId_fkey" },
  { table: "_SpecialtyToVet", name: "_SpecialtyToVet_A_fkey" },
  { table: "_SpecialtyToVet", name: "_SpecialtyToVet_B_fkey" },
] as const;

export async function validateForeignKeys(pool: QueryPool): Promise<void> {
  for (const foreignKey of FOREIGN_KEYS) {
    const state = await pool.query(
      `SELECT constraint_record.convalidated
       FROM pg_constraint AS constraint_record
       JOIN pg_class AS relation
         ON relation.oid = constraint_record.conrelid
       JOIN pg_namespace AS namespace
         ON namespace.oid = relation.relnamespace
       WHERE constraint_record.conname = $1
         AND relation.relname = $2
         AND namespace.nspname = current_schema()`,
      [foreignKey.name, foreignKey.table],
    );
    const row = state.rows[0];
    if (!row) {
      throw new Error(
        `Foreign key ${foreignKey.name} is missing; run Prisma migrations first`,
      );
    }
    if (row.convalidated === true) {
      continue;
    }

    const validation = await pool.query(
      `ALTER TABLE ASYNC "${foreignKey.table}"
       VALIDATE CONSTRAINT "${foreignKey.name}"`,
    );
    const jobId = validation.rows[0]?.job_id;
    if (typeof jobId !== "string" || jobId.length === 0) {
      throw new Error(
        `Validation for ${foreignKey.name} returned no Aurora DSQL job ID`,
      );
    }

    const wait = await pool.query("CALL sys.wait_for_job($1)", [jobId]);
    if (wait.rows[0]?.succeeded !== true) {
      throw new Error(
        `Aurora DSQL validation job ${jobId} for ${foreignKey.name} did not succeed`,
      );
    }
  }
}

async function main(): Promise<void> {
  const host = getRequiredEnv("CLUSTER_ENDPOINT");
  const user = getRequiredEnv("CLUSTER_USER");
  const schema = user === "admin" ? "public" : "myschema";
  const pool = new AuroraDSQLPool({
    host,
    user,
    application_name: "prisma-dsql-fk-validation",
    options: `-c search_path=${schema}`,
  });

  try {
    await validateForeignKeys(pool);
  } finally {
    await pool.end();
  }
}

if (require.main === module) {
  main().catch((error: unknown) => {
    console.error(error);
    process.exit(1);
  });
}
