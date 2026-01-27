/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import org.flywaydb.core.api.configuration.Configuration;
import org.flywaydb.core.internal.database.base.Table;
import org.flywaydb.core.internal.jdbc.JdbcConnectionFactory;
import org.flywaydb.core.internal.jdbc.StatementInterceptor;
import org.flywaydb.database.postgresql.PostgreSQLDatabase;

import java.sql.Connection;
import java.util.logging.Logger;

/**
 * Aurora DSQL database implementation for Flyway.
 *
 * <p>Extends PostgreSQL with DSQL-specific behavior: disables DDL transactions,
 * uses inline PRIMARY KEY constraints, and separates DDL from DML operations.</p>
 */
public class AuroraDSQLDatabase extends PostgreSQLDatabase {

    private static final Logger LOG = Logger.getLogger(AuroraDSQLDatabase.class.getName());
    private static final String PLUGIN_VERSION = "1.0.0";

    public AuroraDSQLDatabase(Configuration configuration,
                              JdbcConnectionFactory jdbcConnectionFactory,
                              StatementInterceptor statementInterceptor) {
        super(configuration, jdbcConnectionFactory, statementInterceptor);
        LOG.info("Using Aurora DSQL Flyway Support v" + PLUGIN_VERSION);
    }

    @Override
    protected AuroraDSQLConnection doGetConnection(Connection connection) {
        return new AuroraDSQLConnection(this, connection);
    }

    @Override
    public boolean supportsDdlTransactions() {
        // DSQL has specific DDL transaction limitations:
        // - Each transaction can only contain 1 DDL statement
        // - Cannot mix DDL and DML in same transaction
        // Returning false ensures Flyway runs each DDL in its own transaction
        return false;
    }

    @Override
    public String getRawCreateScript(Table table, boolean baseline) {
        // DSQL doesn't support ALTER TABLE ADD CONSTRAINT, so we need to define
        // the primary key constraint inline in the CREATE TABLE statement.
        // 
        // IMPORTANT: DSQL only allows ONE DDL statement per transaction.
        // We cannot include CREATE INDEX here - it must be done separately.
        // The index on "success" column is optional for Flyway functionality.
        //
        // NOTE: We intentionally ignore the 'baseline' parameter here.
        // DSQL does not allow DDL and DML in the same transaction, so we cannot
        // include the baseline INSERT statement with the CREATE TABLE.
        // Flyway will handle the baseline INSERT in a separate transaction.
        
        return "CREATE TABLE " + table + " (\n" +
               "    \"installed_rank\" INT NOT NULL PRIMARY KEY,\n" +
               "    \"version\" VARCHAR(50),\n" +
               "    \"description\" VARCHAR(200) NOT NULL,\n" +
               "    \"type\" VARCHAR(20) NOT NULL,\n" +
               "    \"script\" VARCHAR(1000) NOT NULL,\n" +
               "    \"checksum\" INT,\n" +
               "    \"installed_by\" VARCHAR(100) NOT NULL,\n" +
               "    \"installed_on\" TIMESTAMP NOT NULL DEFAULT now(),\n" +
               "    \"execution_time\" INT NOT NULL,\n" +
               "    \"success\" BOOLEAN NOT NULL\n" +
               ")";
    }

    @Override
    public String getInsertStatement(Table table) {
        return "INSERT INTO " + table
                + " (" + quote("installed_rank")
                + ", " + quote("version")
                + ", " + quote("description")
                + ", " + quote("type")
                + ", " + quote("script")
                + ", " + quote("checksum")
                + ", " + quote("installed_by")
                + ", " + quote("execution_time")
                + ", " + quote("success")
                + ")"
                + " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)";
    }

    @Override
    public boolean useSingleConnection() {
        // DSQL requires DDL and DML to be in separate transactions.
        // By returning false, Flyway will use separate connections/transactions
        // for schema history table creation and baseline record insertion.
        return false;
    }
}
