/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import org.flywaydb.core.internal.jdbc.JdbcTemplate;
import org.flywaydb.database.postgresql.PostgreSQLSchema;
import org.flywaydb.database.postgresql.PostgreSQLTable;

import java.sql.SQLException;
import java.util.logging.Logger;

/**
 * Aurora DSQL table implementation for Flyway.
 * 
 * <p>Overrides PostgreSQL table behavior for DSQL compatibility:</p>
 * <ul>
 *   <li>{@link #doLock()} - Skips FOR UPDATE locking (DSQL has restrictions)</li>
 * </ul>
 * 
 * <h2>Why FOR UPDATE Fails</h2>
 * <p>Aurora DSQL requires FOR UPDATE clauses to have equality predicates on the
 * primary key. Flyway's default locking query doesn't include such predicates,
 * causing the error: "locking clause such as FOR UPDATE can be applied only on
 * tables with equality predicates on the key"</p>
 * 
 * <p>Since DSQL provides strong consistency guarantees and the schema history
 * table operations are typically single-threaded during migrations, we can
 * safely skip the explicit row locking.</p>
 */
public class AuroraDSQLTable extends PostgreSQLTable {

    private static final Logger LOG = Logger.getLogger(AuroraDSQLTable.class.getName());

    public AuroraDSQLTable(JdbcTemplate jdbcTemplate, AuroraDSQLDatabase database,
                           PostgreSQLSchema schema, String name) {
        super(jdbcTemplate, database, schema, name);
    }

    /**
     * Locks the table for exclusive access.
     * 
     * <p>Aurora DSQL doesn't support FOR UPDATE without equality predicates on the key.
     * We override to skip explicit locking since:</p>
     * <ul>
     *   <li>DSQL provides strong consistency guarantees</li>
     *   <li>Schema history operations are typically single-threaded</li>
     *   <li>The advisory lock override in AuroraDSQLConnection provides coordination</li>
     * </ul>
     * 
     * <p><b>Note:</b> For production deployments with concurrent migration attempts,
     * consider using external coordination (e.g., distributed locks) or ensuring
     * only one migration process runs at a time.</p>
     */
    @Override
    protected void doLock() throws SQLException {
        // Skip FOR UPDATE locking - DSQL doesn't support it without key equality predicates
        LOG.fine("Skipping FOR UPDATE lock on table " + getName() + " (not supported by Aurora DSQL)");
    }
}
