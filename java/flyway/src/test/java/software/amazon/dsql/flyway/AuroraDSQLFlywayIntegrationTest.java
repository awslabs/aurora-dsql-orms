/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import static org.junit.jupiter.api.Assertions.*;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.MigrationInfo;
import org.flywaydb.core.api.MigrationInfoService;
import org.flywaydb.core.api.output.MigrateResult;
import org.junit.jupiter.api.*;

/**
 * Integration tests for Aurora DSQL Flyway support.
 *
 * <p>These tests verify that Flyway works correctly with Aurora DSQL.
 *
 * <p>Configure via environment variables:
 *
 * <ul>
 *   <li>{@code DSQL_CLUSTER_ENDPOINT} - Cluster endpoint
 * </ul>
 *
 * <p>Run with: {@code DSQL_CLUSTER_ENDPOINT=xxx mvn verify -P integration-test}
 */
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class AuroraDSQLFlywayIntegrationTest {

  private String jdbcUrl;
  private String mainSchema;

  @BeforeAll
  void setUp() throws Exception {
    String clusterEndpoint =
        System.getProperty("dsql.cluster.endpoint", System.getenv("DSQL_CLUSTER_ENDPOINT"));

    if (clusterEndpoint == null || clusterEndpoint.isEmpty()) {
      throw new IllegalStateException("DSQL_CLUSTER_ENDPOINT must be set");
    }

    jdbcUrl = String.format("jdbc:aws-dsql:postgresql://%s:5432/postgres", clusterEndpoint);
    mainSchema = "flyway_main_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);

    System.out.println("=== Aurora DSQL Flyway Integration Test ===");
    System.out.println("Cluster: " + clusterEndpoint);
    System.out.println("Main Schema: " + mainSchema);

    try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
        Statement stmt = conn.createStatement()) {
      stmt.execute("CREATE SCHEMA " + mainSchema);
    }
  }

  @AfterAll
  void tearDown() {
    dropSchema(mainSchema);
  }

  // ==================== Connection Test ====================

  @Test
  @Order(1)
  @DisplayName("Connect to Aurora DSQL")
  void testConnection() throws Exception {
    try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery("SELECT version()")) {
      assertTrue(rs.next());
      String version = rs.getString(1);
      System.out.println("Database version: " + version);
      assertTrue(version.contains("PostgreSQL"), "DSQL should report as PostgreSQL-compatible");
    }
  }

  // ==================== Full Migration Lifecycle ====================

  @Test
  @Order(2)
  @DisplayName("Full migration lifecycle: info -> migrate -> validate -> info")
  void testFullMigrationLifecycle() {
    Flyway flyway =
        Flyway.configure()
            .dataSource(jdbcUrl, "admin", null)
            .schemas(mainSchema)
            .locations("classpath:db/migration/test")
            .load();

    // Info before migrate
    MigrationInfoService infoBefore = flyway.info();
    assertNotNull(infoBefore);
    MigrationInfo[] pending = infoBefore.pending();
    assertTrue(pending.length > 0, "Should have pending migrations");
    System.out.println("Pending migrations: " + pending.length);

    // Migrate
    MigrateResult result = flyway.migrate();
    assertNotNull(result);
    assertTrue(result.success, "Migration should succeed");
    assertTrue(result.migrationsExecuted > 0, "Should execute migrations");
    System.out.println("Migrations executed: " + result.migrationsExecuted);

    // Validate
    assertDoesNotThrow(() -> flyway.validate(), "Validate should pass after migrate");

    // Info after migrate
    MigrationInfo[] applied = flyway.info().applied();
    assertTrue(applied.length > 0, "Should have applied migrations");
    System.out.println("Applied migrations: " + applied.length);

    // Repeated migrate should be idempotent
    MigrateResult repeatResult = flyway.migrate();
    assertTrue(repeatResult.success);
    assertEquals(0, repeatResult.migrationsExecuted, "No new migrations on repeat");
  }

  // ==================== SET ROLE Verification ====================

  @Test
  @Order(3)
  @DisplayName("Multiple Flyway operations work without SET ROLE error")
  void testNoSetRoleError() {
    Flyway flyway =
        Flyway.configure()
            .dataSource(jdbcUrl, "admin", null)
            .schemas(mainSchema)
            .locations("classpath:db/migration/test")
            .load();

    // Multiple operations that would trigger connection state restoration
    for (int i = 0; i < 5; i++) {
      assertDoesNotThrow(() -> flyway.info(), "Flyway info should work without SET ROLE error");
    }
    assertDoesNotThrow(
        () -> flyway.validate(), "Flyway validate should work without SET ROLE error");

    System.out.println("SET ROLE bypass verified");
  }

  // ==================== DDL Verification ====================

  @Test
  @Order(4)
  @DisplayName("DDL operations: CREATE TABLE, ALTER TABLE, CREATE INDEX ASYNC, CREATE VIEW")
  void testDdlOperations() throws Exception {
    try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
        Statement stmt = conn.createStatement()) {

      // CREATE TABLE (V1)
      ResultSet rs =
          stmt.executeQuery(
              "SELECT table_name FROM information_schema.tables "
                  + "WHERE table_schema = '"
                  + mainSchema
                  + "' "
                  + "AND table_name = 'flyway_test_users'");
      assertTrue(rs.next(), "flyway_test_users table should exist");

      // ALTER TABLE ADD COLUMN (V2)
      rs =
          stmt.executeQuery(
              "SELECT column_name FROM information_schema.columns "
                  + "WHERE table_schema = '"
                  + mainSchema
                  + "' "
                  + "AND table_name = 'flyway_test_users' "
                  + "AND column_name = 'status'");
      assertTrue(rs.next(), "status column should exist");

      // CREATE TABLE with UNIQUE (V5)
      rs =
          stmt.executeQuery(
              "SELECT constraint_type FROM information_schema.table_constraints "
                  + "WHERE table_schema = '"
                  + mainSchema
                  + "' "
                  + "AND table_name = 'flyway_test_categories' "
                  + "AND constraint_type = 'UNIQUE'");
      assertTrue(rs.next(), "UNIQUE constraint should exist");

      // CREATE VIEW (repeatable migration R__)
      rs =
          stmt.executeQuery(
              "SELECT table_name FROM information_schema.views "
                  + "WHERE table_schema = '"
                  + mainSchema
                  + "' "
                  + "AND table_name = 'flyway_test_user_summary'");
      assertTrue(rs.next(), "View should exist");
    }
  }

  @Test
  @Order(5)
  @DisplayName("CREATE INDEX ASYNC creates index")
  void testAsyncIndex() throws Exception {
    try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null)) {
      String sql = "SELECT indexname FROM pg_indexes WHERE schemaname = ? AND indexname = ?";

      // Wait for async index with exponential backoff (max ~30 seconds total)
      boolean indexExists = false;
      long sleepMs = 500;
      long totalWaitMs = 0;
      long maxWaitMs = 30000;

      while (!indexExists && totalWaitMs < maxWaitMs) {
        try (PreparedStatement pstmt = conn.prepareStatement(sql)) {
          pstmt.setString(1, mainSchema);
          pstmt.setString(2, "idx_flyway_test_users_email");
          try (ResultSet rs = pstmt.executeQuery()) {
            indexExists = rs.next();
          }
        }
        if (!indexExists) {
          Thread.sleep(sleepMs);
          totalWaitMs += sleepMs;
          sleepMs = Math.min(sleepMs * 2, 4000); // Cap at 4 seconds
        }
      }
      assertTrue(indexExists, "Async index should be created within " + maxWaitMs + "ms");
    }
  }

  // ==================== DML Verification ====================

  @Test
  @Order(6)
  @DisplayName("DML operations: INSERT, UPDATE, DELETE")
  void testDmlOperations() throws Exception {
    try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
        Statement stmt = conn.createStatement()) {

      // INSERT (V4, V6)
      ResultSet rs = stmt.executeQuery("SELECT COUNT(*) FROM " + mainSchema + ".flyway_test_users");
      assertTrue(rs.next());
      assertTrue(rs.getInt(1) >= 1, "Should have users");

      rs = stmt.executeQuery("SELECT COUNT(*) FROM " + mainSchema + ".flyway_test_categories");
      assertTrue(rs.next());
      assertEquals(3, rs.getInt(1), "Should have 3 categories");

      // UPDATE (V8)
      rs =
          stmt.executeQuery(
              "SELECT status FROM "
                  + mainSchema
                  + ".flyway_test_users "
                  + "WHERE email = 'test@example.com'");
      assertTrue(rs.next());
      assertEquals("verified", rs.getString(1), "Status should be updated");

      // DELETE (V8)
      rs =
          stmt.executeQuery(
              "SELECT COUNT(*) FROM "
                  + mainSchema
                  + ".flyway_test_users "
                  + "WHERE email = 'delete_me@example.com'");
      assertTrue(rs.next());
      assertEquals(0, rs.getInt(1), "Deleted record should not exist");
    }
  }

  // ==================== End-to-End Data Verification ====================

  @Test
  @Order(7)
  @DisplayName("End-to-end: insert, update, query view, verify joined data")
  void testEndToEndDataOperations() throws Exception {
    try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
        Statement stmt = conn.createStatement()) {

      // Insert a new user with a category
      ResultSet catRs =
          stmt.executeQuery(
              "SELECT id FROM " + mainSchema + ".flyway_test_categories WHERE name = 'category_a'");
      assertTrue(catRs.next(), "category_a should exist");
      String categoryId = catRs.getString(1);

      // Insert new user linked to category
      stmt.execute(
          "INSERT INTO "
              + mainSchema
              + ".flyway_test_users "
              + "(email, name, status, category_id) VALUES "
              + "('e2e_test@example.com', 'E2E Test User', 'active', '"
              + categoryId
              + "')");

      // Query the view to verify the JOIN works
      ResultSet viewRs =
          stmt.executeQuery(
              "SELECT email, name, status, category_name FROM "
                  + mainSchema
                  + ".flyway_test_user_summary "
                  + "WHERE email = 'e2e_test@example.com'");
      assertTrue(viewRs.next(), "User should be visible in view");
      assertEquals("E2E Test User", viewRs.getString("name"));
      assertEquals("active", viewRs.getString("status"));
      assertEquals(
          "category_a", viewRs.getString("category_name"), "View should join category name");

      // Update the user's status
      stmt.execute(
          "UPDATE "
              + mainSchema
              + ".flyway_test_users "
              + "SET status = 'premium' WHERE email = 'e2e_test@example.com'");

      // Verify update through view
      viewRs =
          stmt.executeQuery(
              "SELECT status FROM "
                  + mainSchema
                  + ".flyway_test_user_summary "
                  + "WHERE email = 'e2e_test@example.com'");
      assertTrue(viewRs.next());
      assertEquals("premium", viewRs.getString("status"), "Status should be updated");

      // Delete and verify
      stmt.execute(
          "DELETE FROM "
              + mainSchema
              + ".flyway_test_users "
              + "WHERE email = 'e2e_test@example.com'");

      viewRs =
          stmt.executeQuery(
              "SELECT COUNT(*) FROM "
                  + mainSchema
                  + ".flyway_test_user_summary "
                  + "WHERE email = 'e2e_test@example.com'");
      assertTrue(viewRs.next());
      assertEquals(0, viewRs.getInt(1), "Deleted user should not appear in view");

      System.out.println("End-to-end data operations verified");
    }
  }

  // ==================== Repeatable Migration ====================

  @Test
  @Order(8)
  @DisplayName("Repeatable migration is applied")
  void testRepeatableMigration() {
    Flyway flyway =
        Flyway.configure()
            .dataSource(jdbcUrl, "admin", null)
            .schemas(mainSchema)
            .locations("classpath:db/migration/test")
            .load();

    MigrationInfo[] applied = flyway.info().applied();
    boolean hasRepeatable = false;
    for (MigrationInfo info : applied) {
      if (info.getVersion() == null) {
        hasRepeatable = true;
        System.out.println("Repeatable migration: " + info.getDescription());
      }
    }
    assertTrue(hasRepeatable, "Should have repeatable migration applied");
  }

  // ==================== Schema History Table ====================

  @Test
  @Order(9)
  @DisplayName("Schema history table has correct structure")
  void testSchemaHistoryStructure() throws Exception {
    try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
        Statement stmt = conn.createStatement()) {

      ResultSet rs =
          stmt.executeQuery(
              "SELECT column_name FROM information_schema.columns "
                  + "WHERE table_schema = '"
                  + mainSchema
                  + "' "
                  + "AND table_name = 'flyway_schema_history' "
                  + "ORDER BY ordinal_position");
      assertTrue(rs.next());
      assertEquals("installed_rank", rs.getString(1));

      rs =
          stmt.executeQuery(
              "SELECT constraint_type FROM information_schema.table_constraints "
                  + "WHERE table_schema = '"
                  + mainSchema
                  + "' "
                  + "AND table_name = 'flyway_schema_history' "
                  + "AND constraint_type = 'PRIMARY KEY'");
      assertTrue(rs.next(), "Schema history should have primary key");
    }
  }

  // ==================== Baseline with baselineOnMigrate ====================

  @Test
  @Order(10)
  @DisplayName("baselineOnMigrate works with DSQL")
  void testBaselineOnMigrate() throws Exception {
    String baselineSchema =
        "flyway_baseline_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);

    try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
        Statement stmt = conn.createStatement()) {
      stmt.execute("CREATE SCHEMA " + baselineSchema);
      // Simulate existing table
      stmt.execute(
          "CREATE TABLE "
              + baselineSchema
              + ".baseline_test ("
              + "id UUID PRIMARY KEY DEFAULT gen_random_uuid(), "
              + "name VARCHAR(255) NOT NULL, "
              + "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)");
    }

    try {
      Flyway flyway =
          Flyway.configure()
              .dataSource(jdbcUrl, "admin", null)
              .schemas(baselineSchema)
              .locations("classpath:db/migration/baseline")
              .baselineOnMigrate(true)
              .baselineVersion("1")
              .load();

      MigrateResult result = flyway.migrate();
      assertTrue(result.success, "Migration with baselineOnMigrate should succeed");

      // Verify V2 was applied (status column added)
      try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
          Statement stmt = conn.createStatement()) {
        ResultSet rs =
            stmt.executeQuery(
                "SELECT column_name FROM information_schema.columns "
                    + "WHERE table_schema = '"
                    + baselineSchema
                    + "' "
                    + "AND table_name = 'baseline_test' "
                    + "AND column_name = 'status'");
        assertTrue(rs.next(), "status column should exist after V2");
      }

      System.out.println("baselineOnMigrate test passed");
    } finally {
      dropSchema(baselineSchema);
    }
  }

  // ==================== Flyway Clean ====================

  @Test
  @Order(11)
  @DisplayName("Flyway clean drops all tables")
  void testFlywayClean() throws Exception {
    String cleanSchema =
        "flyway_clean_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);

    try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
        Statement stmt = conn.createStatement()) {
      stmt.execute("CREATE SCHEMA " + cleanSchema);
    }

    try {
      Flyway flyway =
          Flyway.configure()
              .dataSource(jdbcUrl, "admin", null)
              .schemas(cleanSchema)
              .locations("classpath:db/migration/test")
              .cleanDisabled(false)
              .load();

      flyway.migrate();

      // Verify tables exist
      try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
          Statement stmt = conn.createStatement()) {
        ResultSet rs =
            stmt.executeQuery(
                "SELECT COUNT(*) FROM information_schema.tables "
                    + "WHERE table_schema = '"
                    + cleanSchema
                    + "'");
        assertTrue(rs.next());
        assertTrue(rs.getInt(1) > 0, "Tables should exist before clean");
      }

      flyway.clean();

      // Verify tables dropped
      try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
          Statement stmt = conn.createStatement()) {
        ResultSet rs =
            stmt.executeQuery(
                "SELECT COUNT(*) FROM information_schema.tables "
                    + "WHERE table_schema = '"
                    + cleanSchema
                    + "'");
        assertTrue(rs.next());
        assertEquals(0, rs.getInt(1), "Tables should be dropped after clean");
      }

      System.out.println("Clean test passed");
    } finally {
      dropSchema(cleanSchema);
    }
  }

  // ==================== Helper Methods ====================

  private void dropSchema(String schema) {
    try (Connection conn = DriverManager.getConnection(jdbcUrl, "admin", null);
        Statement stmt = conn.createStatement()) {
      conn.setAutoCommit(true);

      // Get views and tables
      List<String> views =
          queryNames(
              stmt,
              "SELECT table_name FROM information_schema.views WHERE table_schema = ?",
              schema);
      List<String> tables =
          queryNames(
              stmt,
              "SELECT table_name FROM information_schema.tables WHERE table_schema = ?",
              schema);

      // Drop views first, then tables, then schema
      for (String view : views) {
        stmt.execute("DROP VIEW IF EXISTS " + schema + ".\"" + view + "\"");
      }
      for (String table : tables) {
        stmt.execute("DROP TABLE IF EXISTS " + schema + ".\"" + table + "\"");
      }
      stmt.execute("DROP SCHEMA IF EXISTS " + schema);
    } catch (Exception e) {
      System.err.println("Cleanup warning for " + schema + ": " + e.getMessage());
    }
  }

  private List<String> queryNames(Statement stmt, String sql, String schema) throws SQLException {
    List<String> names = new ArrayList<>();
    try (java.sql.PreparedStatement pstmt = stmt.getConnection().prepareStatement(sql)) {
      pstmt.setString(1, schema);
      try (ResultSet rs = pstmt.executeQuery()) {
        while (rs.next()) {
          names.add(rs.getString(1));
        }
      }
    }
    return names;
  }
}
