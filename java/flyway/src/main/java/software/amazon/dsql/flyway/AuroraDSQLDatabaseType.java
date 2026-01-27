/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import org.flywaydb.core.api.configuration.Configuration;
import org.flywaydb.core.internal.database.base.Database;
import org.flywaydb.core.internal.jdbc.JdbcConnectionFactory;
import org.flywaydb.core.internal.jdbc.StatementInterceptor;
import org.flywaydb.database.postgresql.PostgreSQLDatabaseType;

import java.sql.Connection;
import java.sql.SQLException;

/**
 * Flyway database type for Amazon Aurora DSQL.
 * 
 * <p>Extends PostgreSQL support to handle the aws-dsql JDBC URL prefix
 * and work around DSQL-specific limitations:</p>
 * <ul>
 *   <li>SET ROLE not supported (uses IAM authentication)</li>
 *   <li>One DDL statement per transaction</li>
 *   <li>No foreign key constraints</li>
 *   <li>CREATE INDEX must use ASYNC keyword</li>
 * </ul>
 * 
 * <p>This plugin is discovered via Java SPI (ServiceLoader) when the JAR
 * is on the classpath. Register in META-INF/services/org.flywaydb.core.extensibility.Plugin</p>
 * 
 * <p><b>Important:</b> The Aurora DSQL JDBC Connector transforms URLs from
 * {@code jdbc:aws-dsql:postgresql://...} to {@code jdbc:postgresql://...} internally.
 * We detect DSQL connections by checking both the original URL format AND by
 * detecting DSQL endpoints in the hostname (*.dsql.*.on.aws).</p>
 * 
 * @see <a href="https://docs.aws.amazon.com/aurora-dsql/latest/userguide/">Aurora DSQL Documentation</a>
 */
public class AuroraDSQLDatabaseType extends PostgreSQLDatabaseType {

    // Pattern to detect DSQL endpoints: *.dsql.<region>.on.aws
    private static final String DSQL_ENDPOINT_PATTERN = ".dsql.";
    private static final String DSQL_ENDPOINT_SUFFIX = ".on.aws";

    @Override
    public String getName() {
        return "Aurora DSQL";
    }

    @Override
    public boolean handlesJDBCUrl(String url) {
        // Handle explicit jdbc:aws-dsql: prefix
        if (url.startsWith("jdbc:aws-dsql:")) {
            return true;
        }
        
        // Also detect DSQL by endpoint pattern in the URL
        // The DSQL JDBC connector transforms jdbc:aws-dsql:postgresql://... to jdbc:postgresql://...
        // but the hostname still contains the DSQL endpoint pattern
        // Example: jdbc:postgresql://abc123.dsql.us-east-1.on.aws:5432/postgres
        if (url.startsWith("jdbc:postgresql://") && 
            url.contains(DSQL_ENDPOINT_PATTERN) && 
            url.contains(DSQL_ENDPOINT_SUFFIX)) {
            return true;
        }
        
        return false;
    }

    @Override
    public int getPriority() {
        // Higher priority than PostgreSQL (default 0) to ensure DSQL URLs are matched first
        return 1;
    }

    @Override
    public boolean handlesDatabaseProductNameAndVersion(String databaseProductName, 
                                                         String databaseProductVersion, 
                                                         Connection connection) {
        // Check if this is a DSQL connection by examining the connection URL
        try {
            String url = connection.getMetaData().getURL();
            if (url != null && url.contains(DSQL_ENDPOINT_PATTERN) && url.contains(DSQL_ENDPOINT_SUFFIX)) {
                return true;
            }
        } catch (SQLException e) {
            // Fall through to return false
        }
        return false;
    }

    @Override
    public String getDriverClass(String url, ClassLoader classLoader) {
        // Use the Aurora DSQL JDBC Connector driver for aws-dsql URLs
        if (url.startsWith("jdbc:aws-dsql:")) {
            return "software.amazon.dsql.jdbc.DSQLConnector";
        }
        // For transformed URLs (jdbc:postgresql://), use standard PostgreSQL driver
        return "org.postgresql.Driver";
    }

    @Override
    public Database createDatabase(Configuration configuration, 
                                   JdbcConnectionFactory jdbcConnectionFactory,
                                   StatementInterceptor statementInterceptor) {
        return new AuroraDSQLDatabase(configuration, jdbcConnectionFactory, statementInterceptor);
    }

    @Override
    public String getPluginVersion(Configuration config) {
        return "1.0.0";
    }
}
