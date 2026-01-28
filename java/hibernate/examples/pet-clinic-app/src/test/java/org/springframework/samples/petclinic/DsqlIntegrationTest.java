/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

package org.springframework.samples.petclinic;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

/**
 * Integration test for Aurora DSQL JDBC Connector.
 *
 * @author AWS
 */
@EnabledIfEnvironmentVariable(named = "RUN_INTEGRATION", matches = "TRUE")
class DsqlIntegrationTest {

  private static final String CLUSTER_ENDPOINT = System.getenv("CLUSTER_ENDPOINT");

  private static final String CLUSTER_USER =
      System.getenv("CLUSTER_USER") != null ? System.getenv("CLUSTER_USER") : "admin";

  @BeforeAll
  static void setUp() {
    assertNotNull(CLUSTER_ENDPOINT, "CLUSTER_ENDPOINT environment variable must be set");
  }

  @Test
  void testJdbcConnectorConnection() throws SQLException {
    String url =
        "jdbc:aws-dsql:postgresql://" + CLUSTER_ENDPOINT + "/postgres?user=" + CLUSTER_USER;

    try (Connection conn = DriverManager.getConnection(url)) {
      assertNotNull(conn, "Connection should not be null");
      assertFalse(conn.isClosed(), "Connection should be open");

      try (Statement stmt = conn.createStatement();
          ResultSet rs = stmt.executeQuery("SELECT 1 as test_value")) {
        rs.next();
        assertEquals(1, rs.getInt("test_value"));
      }
    }
  }
}
