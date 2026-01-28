/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.concurrent.Callable;
import java.util.logging.Logger;
import org.flywaydb.core.internal.database.base.Schema;
import org.flywaydb.core.internal.database.base.Table;
import org.flywaydb.core.internal.exception.FlywaySqlException;
import org.flywaydb.database.postgresql.PostgreSQLConnection;

/**
 * Aurora DSQL connection implementation for Flyway.
 *
 * <p>Overrides PostgreSQL connection behavior: skips SET ROLE (DSQL uses IAM auth), bypasses
 * advisory locks (DSQL uses OCC), and returns DSQL-compatible schemas.
 */
public class AuroraDSQLConnection extends PostgreSQLConnection {

  private static final Logger LOG = Logger.getLogger(AuroraDSQLConnection.class.getName());

  public AuroraDSQLConnection(AuroraDSQLDatabase database, Connection connection) {
    super(database, connection);
  }

  /** Skips SET ROLE restoration - DSQL uses IAM authentication where role is fixed. */
  @Override
  protected void doRestoreOriginalState() throws SQLException {
    LOG.fine("Skipping SET ROLE restoration (not supported by Aurora DSQL)");
  }

  @Override
  public Schema getSchema(String name) {
    return new AuroraDSQLSchema(jdbcTemplate, (AuroraDSQLDatabase) database, name);
  }

  /**
   * Executes the callable without advisory locks (not supported by DSQL). DSQL's optimistic
   * concurrency control handles conflicts.
   */
  @Override
  public <T> T lock(Table table, Callable<T> callable) {
    LOG.fine("Executing without advisory lock (not supported by Aurora DSQL)");
    try {
      return callable.call();
    } catch (SQLException e) {
      throw new FlywaySqlException("Unable to execute migration", e);
    } catch (RuntimeException e) {
      throw e;
    } catch (Exception e) {
      throw new RuntimeException("Unable to execute migration", e);
    }
  }
}
