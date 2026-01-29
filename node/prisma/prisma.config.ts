/**
 * Prisma configuration for CLI integration tests.
 *
 * This file exists at the package root (rather than in test/) because Prisma
 * looks for prisma.config.ts in the current working directory when running
 * commands like `prisma migrate diff`. The CLI integration tests run from
 * the package root, so this configuration enables those tests to work.
 *
 * The veterinary-schema.prisma in ./prisma is used as a test fixture for
 * validating the CLI tools work correctly with a realistic schema.
 */
import * as path from "node:path";
import { defineConfig } from "prisma/config";

async function extractRegionFromEndpoint(endpoint: string): Promise<string> {
  const match = endpoint.match(
    /^[a-z0-9]+\.dsql(?:-[^.]+)?\.([a-z0-9-]+)\.on\.aws$/,
  );
  if (!match?.[1]) {
    throw new Error(`Unknown DSQL endpoint format: ${endpoint}`);
  }
  return match[1];
}

async function getDatabaseUrl(): Promise<string> {
  const endpoint = process.env.CLUSTER_ENDPOINT;
  if (!endpoint) {
    // When no endpoint is configured, return a placeholder URL.
    // This allows commands like `prisma migrate diff --from-empty` to work
    // since they don't actually connect to a database.
    return "postgresql://localhost:5432/postgres";
  }

  const { DsqlSigner } = await import("@aws-sdk/dsql-signer");

  const user = process.env.CLUSTER_USER ?? "admin";
  const region =
    process.env.AWS_REGION ?? (await extractRegionFromEndpoint(endpoint));
  const schema = user === "admin" ? "public" : "myschema";

  const signer = new DsqlSigner({ hostname: endpoint, region });
  const token =
    user === "admin"
      ? await signer.getDbConnectAdminAuthToken()
      : await signer.getDbConnectAuthToken();
  const encodedToken = encodeURIComponent(token);

  return `postgresql://${user}:${encodedToken}@${endpoint}:5432/postgres?sslmode=verify-full&schema=${schema}`;
}

export default defineConfig({
  schema: path.join(__dirname, "prisma", "veterinary-schema.prisma"),
  migrations: {
    path: path.join(__dirname, "prisma", "migrations"),
  },
  datasource: {
    url: await getDatabaseUrl(),
  },
});
