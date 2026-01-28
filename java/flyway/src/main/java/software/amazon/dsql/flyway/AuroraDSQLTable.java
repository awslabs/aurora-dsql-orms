/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import java.sql.SQLException;
import java.util.logging.Logger;
import org.flywaydb.core.internal.jdbc.JdbcTemplate;
import org.flywaydb.database.postgresql.PostgreSQLSchema;
import org.flywaydb.database.postgresql.PostgreSQLTable;

/**
 * Aurora DSQL table implementation for Flyway.
 *
 * <p>Skips FOR UPDATE locking since DSQL requires equality predicates on the key which Flyway's
 * default locking query doesn't provide.
 */
public class AuroraDSQLTable extends PostgreSQLTable {

  private static final Logger LOG = Logger.getLogger(AuroraDSQLTable.class.getName());

  public AuroraDSQLTable(
      JdbcTemplate jdbcTemplate,
      AuroraDSQLDatabase database,
      PostgreSQLSchema schema,
      String name) {
    super(jdbcTemplate, database, schema, name);
  }

  /**
   * Skips FOR UPDATE locking - DSQL requires key equality predicates which Flyway doesn't provide.
   */
  @Override
  protected void doLock() throws SQLException {
    LOG.fine("Skipping FOR UPDATE lock on table " + getName() + " (not supported by Aurora DSQL)");
  }
}
