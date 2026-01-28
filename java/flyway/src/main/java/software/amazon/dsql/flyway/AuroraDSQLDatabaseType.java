/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import java.sql.Connection;
import java.sql.SQLException;
import org.flywaydb.core.api.configuration.Configuration;
import org.flywaydb.core.internal.database.base.Database;
import org.flywaydb.core.internal.jdbc.JdbcConnectionFactory;
import org.flywaydb.core.internal.jdbc.StatementInterceptor;
import org.flywaydb.database.postgresql.PostgreSQLDatabaseType;

/**
 * Flyway database type for Amazon Aurora DSQL.
 *
 * <p>Extends PostgreSQL support to handle {@code jdbc:aws-dsql:} URLs and DSQL-specific behaviors.
 * Discovered via Java SPI when the JAR is on the classpath.
 *
 * <p>The Aurora DSQL JDBC Connector transforms URLs from {@code jdbc:aws-dsql:postgresql://} to
 * {@code jdbc:postgresql://} internally. We detect DSQL by both URL prefix and endpoint pattern
 * (*.dsql.*). This supports both public endpoints and PrivateLink endpoints.
 */
public class AuroraDSQLDatabaseType extends PostgreSQLDatabaseType {

  // Patterns to detect DSQL endpoints
  // Public endpoints: <cluster-id>.dsql.<region>.on.aws
  // PrivateLink endpoints: <cluster-id>.dsql-fnh4.<region>.on.aws
  private static final String DSQL_PUBLIC_PATTERN = ".dsql.";
  private static final String DSQL_PRIVATELINK_PATTERN = ".dsql-";

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
    // Supports both public (*.dsql.<region>.on.aws) and PrivateLink (*.dsql-*) endpoints
    if (url.startsWith("jdbc:postgresql://")
        && (url.contains(DSQL_PUBLIC_PATTERN) || url.contains(DSQL_PRIVATELINK_PATTERN))) {
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
  public boolean handlesDatabaseProductNameAndVersion(
      String databaseProductName, String databaseProductVersion, Connection connection) {
    // Check if this is a DSQL connection by examining the connection URL
    try {
      String url = connection.getMetaData().getURL();
      if (url != null
          && (url.contains(DSQL_PUBLIC_PATTERN) || url.contains(DSQL_PRIVATELINK_PATTERN))) {
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
  public Database createDatabase(
      Configuration configuration,
      JdbcConnectionFactory jdbcConnectionFactory,
      StatementInterceptor statementInterceptor) {
    return new AuroraDSQLDatabase(configuration, jdbcConnectionFactory, statementInterceptor);
  }

  @Override
  public String getPluginVersion(Configuration config) {
    return "1.0.0";
  }
}
