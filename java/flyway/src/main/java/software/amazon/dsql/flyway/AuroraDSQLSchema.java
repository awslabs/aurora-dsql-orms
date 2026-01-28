/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Logger;
import org.flywaydb.core.internal.database.base.Table;
import org.flywaydb.core.internal.jdbc.JdbcTemplate;
import org.flywaydb.database.postgresql.PostgreSQLSchema;

/**
 * Aurora DSQL schema implementation for Flyway.
 *
 * <p>Handles DSQL-specific behavior:
 *
 * <ul>
 *   <li>{@link #getTable(String)} - Returns DSQL-compatible tables
 *   <li>{@link #doClean()} - Drops views then tables, one DDL per transaction
 * </ul>
 */
public class AuroraDSQLSchema extends PostgreSQLSchema {

  private static final Logger LOG = Logger.getLogger(AuroraDSQLSchema.class.getName());

  public AuroraDSQLSchema(JdbcTemplate jdbcTemplate, AuroraDSQLDatabase database, String name) {
    super(jdbcTemplate, database, name);
  }

  @Override
  public Table getTable(String tableName) {
    return new AuroraDSQLTable(jdbcTemplate, (AuroraDSQLDatabase) database, this, tableName);
  }

  /**
   * Cleans the schema by dropping all objects one at a time.
   *
   * <p>Aurora DSQL only allows one DDL statement per transaction. This method drops views first
   * (they depend on tables), then tables, with autocommit enabled so each DROP is its own
   * transaction.
   */
  @Override
  protected void doClean() throws SQLException {
    Connection conn = jdbcTemplate.getConnection();
    boolean originalAutoCommit = conn.getAutoCommit();

    try {
      conn.setAutoCommit(true);

      // Drop views first (they depend on tables)
      List<String> views = getViews(conn);
      for (String view : views) {
        String dropSql = "DROP VIEW IF EXISTS " + database.quote(name, view);
        LOG.fine("Dropping view: " + dropSql);
        try (Statement stmt = conn.createStatement()) {
          stmt.execute(dropSql);
        }
      }

      // Drop tables
      Table[] tables = allTables();
      for (Table table : tables) {
        String dropSql = "DROP TABLE IF EXISTS " + database.quote(name, table.getName());
        LOG.fine("Dropping table: " + dropSql);
        try (Statement stmt = conn.createStatement()) {
          stmt.execute(dropSql);
        }
      }
    } finally {
      conn.setAutoCommit(originalAutoCommit);
    }
  }

  private List<String> getViews(Connection conn) throws SQLException {
    List<String> views = new ArrayList<>();
    String sql = "SELECT table_name FROM information_schema.views WHERE table_schema = ?";
    try (java.sql.PreparedStatement pstmt = conn.prepareStatement(sql)) {
      pstmt.setString(1, name);
      try (ResultSet rs = pstmt.executeQuery()) {
        while (rs.next()) {
          views.add(rs.getString(1));
        }
      }
    }
    return views;
  }
}
