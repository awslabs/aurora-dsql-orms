/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Method;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for AuroraDSQLDatabase and related classes.
 *
 * <p>These tests verify the class hierarchy and method signatures without requiring a database
 * connection. Behavioral tests are in integration tests.
 */
class AuroraDSQLDatabaseTest {

  @Test
  @DisplayName("AuroraDSQLDatabase should extend PostgreSQLDatabase")
  void databaseExtendsPostgresql() {
    assertTrue(
        org.flywaydb.database.postgresql.PostgreSQLDatabase.class.isAssignableFrom(
            AuroraDSQLDatabase.class),
        "AuroraDSQLDatabase should extend PostgreSQLDatabase");
  }

  @Test
  @DisplayName("AuroraDSQLConnection should extend PostgreSQLConnection")
  void connectionExtendsPostgresql() {
    assertTrue(
        org.flywaydb.database.postgresql.PostgreSQLConnection.class.isAssignableFrom(
            AuroraDSQLConnection.class),
        "AuroraDSQLConnection should extend PostgreSQLConnection");
  }

  @Test
  @DisplayName("AuroraDSQLDatabaseType should extend PostgreSQLDatabaseType")
  void databaseTypeExtendsPostgresql() {
    assertTrue(
        org.flywaydb.database.postgresql.PostgreSQLDatabaseType.class.isAssignableFrom(
            AuroraDSQLDatabaseType.class),
        "AuroraDSQLDatabaseType should extend PostgreSQLDatabaseType");
  }

  @Test
  @DisplayName("AuroraDSQLDatabase.supportsDdlTransactions() should be overridden")
  void supportsDdlTransactionsIsOverridden() throws NoSuchMethodException {
    Method method = AuroraDSQLDatabase.class.getDeclaredMethod("supportsDdlTransactions");
    assertEquals(
        AuroraDSQLDatabase.class,
        method.getDeclaringClass(),
        "supportsDdlTransactions should be declared in AuroraDSQLDatabase (overridden from"
            + " parent)");
  }

  @Test
  @DisplayName("AuroraDSQLDatabase.getRawCreateScript() should be overridden")
  void getRawCreateScriptIsOverridden() throws NoSuchMethodException {
    Method method =
        AuroraDSQLDatabase.class.getDeclaredMethod(
            "getRawCreateScript",
            org.flywaydb.core.internal.database.base.Table.class,
            boolean.class);
    assertEquals(
        AuroraDSQLDatabase.class,
        method.getDeclaringClass(),
        "getRawCreateScript should be declared in AuroraDSQLDatabase (overridden from parent)");
  }

  @Test
  @DisplayName("AuroraDSQLDatabase.doGetConnection() should be overridden")
  void doGetConnectionIsOverridden() throws NoSuchMethodException {
    Method method =
        AuroraDSQLDatabase.class.getDeclaredMethod("doGetConnection", java.sql.Connection.class);
    assertEquals(
        AuroraDSQLDatabase.class,
        method.getDeclaringClass(),
        "doGetConnection should be declared in AuroraDSQLDatabase (overridden from parent)");
  }

  @Test
  @DisplayName("AuroraDSQLConnection.doRestoreOriginalState() should be overridden")
  void doRestoreOriginalStateIsOverridden() throws NoSuchMethodException {
    Method method = AuroraDSQLConnection.class.getDeclaredMethod("doRestoreOriginalState");
    assertEquals(
        AuroraDSQLConnection.class,
        method.getDeclaringClass(),
        "doRestoreOriginalState should be declared in AuroraDSQLConnection (overridden from"
            + " parent)");
  }

  @Test
  @DisplayName("AuroraDSQLConnection.lock() should be overridden")
  void lockIsOverridden() throws NoSuchMethodException {
    Method method =
        AuroraDSQLConnection.class.getDeclaredMethod(
            "lock",
            org.flywaydb.core.internal.database.base.Table.class,
            java.util.concurrent.Callable.class);
    assertEquals(
        AuroraDSQLConnection.class,
        method.getDeclaringClass(),
        "lock should be declared in AuroraDSQLConnection (overridden from parent)");
  }

  @Test
  @DisplayName("AuroraDSQLConnection.getSchema() should be overridden")
  void getSchemaIsOverridden() throws NoSuchMethodException {
    Method method = AuroraDSQLConnection.class.getDeclaredMethod("getSchema", String.class);
    assertEquals(
        AuroraDSQLConnection.class,
        method.getDeclaringClass(),
        "getSchema should be declared in AuroraDSQLConnection (overridden from parent)");
  }

  @Test
  @DisplayName("AuroraDSQLTable.doLock() should be overridden")
  void doLockIsOverridden() throws NoSuchMethodException {
    Method method = AuroraDSQLTable.class.getDeclaredMethod("doLock");
    assertEquals(
        AuroraDSQLTable.class,
        method.getDeclaringClass(),
        "doLock should be declared in AuroraDSQLTable (overridden from parent)");
  }

  @Test
  @DisplayName("AuroraDSQLSchema.getTable() should be overridden")
  void getTableIsOverridden() throws NoSuchMethodException {
    Method method = AuroraDSQLSchema.class.getDeclaredMethod("getTable", String.class);
    assertEquals(
        AuroraDSQLSchema.class,
        method.getDeclaringClass(),
        "getTable should be declared in AuroraDSQLSchema (overridden from parent)");
  }
}
