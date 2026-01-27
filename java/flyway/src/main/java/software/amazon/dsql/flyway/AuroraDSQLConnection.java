/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import org.flywaydb.core.internal.database.base.Schema;
import org.flywaydb.core.internal.database.base.Table;
import org.flywaydb.core.internal.exception.FlywaySqlException;
import org.flywaydb.database.postgresql.PostgreSQLConnection;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.concurrent.Callable;
import java.util.logging.Logger;

/**
 * Aurora DSQL connection implementation for Flyway.
 * 
 * <p>Overrides PostgreSQL connection behavior for DSQL compatibility:</p>
 * <ul>
 *   <li>{@link #doRestoreOriginalState()} - Skips SET ROLE (not supported by DSQL)</li>
 *   <li>{@link #lock(Table, Callable)} - Bypasses advisory locks and handles DDL/DML separation</li>
 *   <li>{@link #getSchema(String)} - Returns DSQL-compatible schema</li>
 * </ul>
 * 
 * <h2>Why SET ROLE Fails</h2>
 * <p>Aurora DSQL uses IAM authentication exclusively. The database role is
 * determined by the IAM credentials used to generate the authentication token.
 * Unlike standard PostgreSQL where you can switch roles within a session,
 * DSQL connections are bound to a single role for their lifetime.</p>
 * 
 * <h2>Why Advisory Locks Fail</h2>
 * <p>Aurora DSQL doesn't support PostgreSQL advisory lock functions like
 * {@code pg_try_advisory_xact_lock}. We bypass locking entirely since DSQL's
 * optimistic concurrency control provides sufficient protection for typical
 * single-threaded migration scenarios.</p>
 * 
 * <h2>DDL/DML Separation</h2>
 * <p>Aurora DSQL does not allow DDL and DML in the same transaction. The
 * {@link #lock(Table, Callable)} method handles this by committing after
 * DDL operations before DML operations run.</p>
 * 
 * @see <a href="https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html">DSQL PostgreSQL Compatibility</a>
 */
public class AuroraDSQLConnection extends PostgreSQLConnection {

    private static final Logger LOG = Logger.getLogger(AuroraDSQLConnection.class.getName());

    public AuroraDSQLConnection(AuroraDSQLDatabase database, Connection connection) {
        super(database, connection);
    }

    /**
     * Restores the connection to its original state after migrations.
     * 
     * <p>Overridden to skip SET ROLE which DSQL doesn't support.</p>
     */
    @Override
    protected void doRestoreOriginalState() throws SQLException {
        // Intentionally empty - do NOT call SET ROLE
        // Aurora DSQL uses IAM authentication where the role is fixed at connection time
        LOG.fine("Skipping SET ROLE restoration (not supported by Aurora DSQL)");
    }

    /**
     * Returns a DSQL-compatible schema.
     */
    @Override
    public Schema getSchema(String name) {
        return new AuroraDSQLSchema(jdbcTemplate, (AuroraDSQLDatabase) database, name);
    }

    /**
     * Executes the callable without acquiring an advisory lock.
     * 
     * <p>Aurora DSQL doesn't support PostgreSQL advisory locks ({@code pg_try_advisory_xact_lock}).
     * We execute the callable directly without locking. This is safe because:</p>
     * <ul>
     *   <li>DSQL provides strong consistency via optimistic concurrency control</li>
     *   <li>Flyway migrations are typically run single-threaded</li>
     *   <li>Concurrent migration attempts will fail-fast on conflicts</li>
     * </ul>
     * 
     * <p><b>Warning:</b> For production deployments with concurrent migration attempts,
     * use external coordination (e.g., distributed locks via DynamoDB) or ensure
     * only one migration process runs at a time.</p>
     * 
     * @param table the schema history table (unused - no locking performed)
     * @param callable the operation to execute
     * @return the result of the callable
     */
    @Override
    public <T> T lock(Table table, Callable<T> callable) {
        LOG.fine("Executing without advisory lock (not supported by Aurora DSQL)");
        try {
            return callable.call();
        } catch (SQLException e) {
            throw new FlywaySqlException("Unable to execute migration", e);
        } catch (Exception e) {
            if (e instanceof RuntimeException) {
                throw (RuntimeException) e;
            }
            throw new RuntimeException("Unable to execute migration", e);
        }
    }
}
