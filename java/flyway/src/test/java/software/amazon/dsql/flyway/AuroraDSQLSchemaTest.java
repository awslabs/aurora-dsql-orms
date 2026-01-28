/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Method;
import java.sql.SQLException;
import org.flywaydb.core.internal.database.base.Table;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for AuroraDSQLSchema.
 *
 * <p>These tests verify method signatures and overrides. Basic override test for getTable() is in
 * AuroraDSQLDatabaseTest.
 */
class AuroraDSQLSchemaTest {

  @Test
  @DisplayName("AuroraDSQLSchema should extend PostgreSQLSchema")
  void schemaExtendsPostgresql() {
    assertTrue(
        org.flywaydb.database.postgresql.PostgreSQLSchema.class.isAssignableFrom(
            AuroraDSQLSchema.class),
        "AuroraDSQLSchema should extend PostgreSQLSchema");
  }

  @Test
  @DisplayName("getTable() should return Table type")
  void getTableReturnType() throws NoSuchMethodException {
    Method method = AuroraDSQLSchema.class.getDeclaredMethod("getTable", String.class);
    assertEquals(Table.class, method.getReturnType(), "getTable should return Table");
  }

  @Test
  @DisplayName("doClean() should be overridden")
  void doCleanIsOverridden() throws NoSuchMethodException {
    Method method = AuroraDSQLSchema.class.getDeclaredMethod("doClean");
    assertEquals(
        AuroraDSQLSchema.class,
        method.getDeclaringClass(),
        "doClean should be declared in AuroraDSQLSchema");
  }

  @Test
  @DisplayName("doClean() should declare SQLException")
  void doCleanDeclaresSqlException() throws NoSuchMethodException {
    Method method = AuroraDSQLSchema.class.getDeclaredMethod("doClean");
    Class<?>[] exceptionTypes = method.getExceptionTypes();

    assertEquals(1, exceptionTypes.length);
    assertEquals(SQLException.class, exceptionTypes[0]);
  }

  @Test
  @DisplayName("doClean() should be protected")
  void doCleanIsProtected() throws NoSuchMethodException {
    Method method = AuroraDSQLSchema.class.getDeclaredMethod("doClean");
    int modifiers = method.getModifiers();

    assertTrue(java.lang.reflect.Modifier.isProtected(modifiers), "doClean should be protected");
  }

  @Test
  @DisplayName("Schema has getViews helper method")
  void hasGetViewsMethod() throws NoSuchMethodException {
    // getViews is a private helper method for dropping views before tables
    Method method = AuroraDSQLSchema.class.getDeclaredMethod("getViews", java.sql.Connection.class);
    assertTrue(
        java.lang.reflect.Modifier.isPrivate(method.getModifiers()), "getViews should be private");
  }
}
