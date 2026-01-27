/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for AuroraDSQLDatabaseType.
 * These tests don't require a database connection.
 */
class AuroraDSQLDatabaseTypeTest {

    private final AuroraDSQLDatabaseType databaseType = new AuroraDSQLDatabaseType();

    @Test
    @DisplayName("Should handle jdbc:aws-dsql:postgresql:// URL")
    void handlesAwsDsqlUrl() {
        assertTrue(databaseType.handlesJDBCUrl(
            "jdbc:aws-dsql:postgresql://abc123.dsql.us-east-1.on.aws/postgres"));
    }

    @Test
    @DisplayName("Should handle jdbc:aws-dsql:postgresql:// URL with port")
    void handlesAwsDsqlUrlWithPort() {
        assertTrue(databaseType.handlesJDBCUrl(
            "jdbc:aws-dsql:postgresql://abc123.dsql.us-east-1.on.aws:5432/postgres"));
    }

    @Test
    @DisplayName("Should handle jdbc:aws-dsql:// URL without postgresql prefix")
    void handlesAwsDsqlUrlWithoutPostgresqlPrefix() {
        assertTrue(databaseType.handlesJDBCUrl(
            "jdbc:aws-dsql://abc123.dsql.us-east-1.on.aws/postgres"));
    }

    @Test
    @DisplayName("Should handle transformed jdbc:postgresql:// URL with DSQL endpoint")
    void handlesTransformedPostgresqlUrlWithDsqlEndpoint() {
        // The DSQL JDBC connector transforms jdbc:aws-dsql:postgresql:// to jdbc:postgresql://
        // but the hostname still contains the DSQL endpoint pattern
        assertTrue(databaseType.handlesJDBCUrl(
            "jdbc:postgresql://abc123.dsql.us-east-1.on.aws:5432/postgres"));
    }

    @Test
    @DisplayName("Should handle transformed URL with different regions")
    void handlesTransformedUrlWithDifferentRegions() {
        assertTrue(databaseType.handlesJDBCUrl(
            "jdbc:postgresql://xyz789.dsql.eu-west-1.on.aws:5432/postgres"));
        assertTrue(databaseType.handlesJDBCUrl(
            "jdbc:postgresql://cluster.dsql.ap-southeast-2.on.aws:5432/postgres"));
    }

    @Test
    @DisplayName("Should NOT handle standard jdbc:postgresql:// URL to localhost")
    void doesNotHandleStandardPostgresqlUrl() {
        assertFalse(databaseType.handlesJDBCUrl(
            "jdbc:postgresql://localhost:5432/mydb"));
    }

    @Test
    @DisplayName("Should NOT handle standard jdbc:postgresql:// URL to RDS")
    void doesNotHandleRdsPostgresqlUrl() {
        assertFalse(databaseType.handlesJDBCUrl(
            "jdbc:postgresql://mydb.abc123.us-east-1.rds.amazonaws.com:5432/mydb"));
    }

    @Test
    @DisplayName("Should NOT handle jdbc:mysql:// URL")
    void doesNotHandleMysqlUrl() {
        assertFalse(databaseType.handlesJDBCUrl(
            "jdbc:mysql://localhost:3306/mydb"));
    }

    @Test
    @DisplayName("Should NOT handle jdbc:oracle:// URL")
    void doesNotHandleOracleUrl() {
        assertFalse(databaseType.handlesJDBCUrl(
            "jdbc:oracle:thin:@localhost:1521:xe"));
    }

    @Test
    @DisplayName("Should have higher priority than PostgreSQL (priority > 0)")
    void hasHigherPriorityThanPostgresql() {
        // PostgreSQL default priority is 0
        assertTrue(databaseType.getPriority() > 0, 
            "DSQL should have higher priority than PostgreSQL to match first");
    }

    @Test
    @DisplayName("Should return 'Aurora DSQL' as database name")
    void returnsCorrectName() {
        assertEquals("Aurora DSQL", databaseType.getName());
    }

    @Test
    @DisplayName("Should return plugin version")
    void returnsPluginVersion() {
        String version = databaseType.getPluginVersion(null);
        assertNotNull(version);
        assertEquals("1.0.0", version);
    }

    @Test
    @DisplayName("Should return DSQL JDBC driver class for aws-dsql URLs")
    void returnsCorrectDriverClassForDsqlUrl() {
        String driverClass = databaseType.getDriverClass(
            "jdbc:aws-dsql:postgresql://abc123.dsql.us-east-1.on.aws/postgres", 
            null);
        assertEquals("software.amazon.dsql.jdbc.DSQLConnector", driverClass);
    }

    @Test
    @DisplayName("Should return PostgreSQL driver class for transformed URLs")
    void returnsPostgresDriverClassForTransformedUrl() {
        String driverClass = databaseType.getDriverClass(
            "jdbc:postgresql://abc123.dsql.us-east-1.on.aws:5432/postgres", 
            null);
        assertEquals("org.postgresql.Driver", driverClass);
    }
}
