/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import java.lang.reflect.Method;
import java.sql.SQLException;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for AuroraDSQLTable.
 *
 * <p>These tests verify method signatures and overrides.
 * Basic override test for doLock() is in AuroraDSQLDatabaseTest.</p>
 */
class AuroraDSQLTableTest {

    @Test
    @DisplayName("AuroraDSQLTable should extend PostgreSQLTable")
    void tableExtendsPostgresql() {
        assertTrue(
            org.flywaydb.database.postgresql.PostgreSQLTable.class
                .isAssignableFrom(AuroraDSQLTable.class),
            "AuroraDSQLTable should extend PostgreSQLTable"
        );
    }

    @Test
    @DisplayName("doLock() should declare SQLException")
    void doLockDeclaresSqlException() throws NoSuchMethodException {
        Method method = AuroraDSQLTable.class.getDeclaredMethod("doLock");
        Class<?>[] exceptionTypes = method.getExceptionTypes();

        assertEquals(1, exceptionTypes.length);
        assertEquals(SQLException.class, exceptionTypes[0]);
    }

    @Test
    @DisplayName("doLock() should be protected")
    void doLockIsProtected() throws NoSuchMethodException {
        Method method = AuroraDSQLTable.class.getDeclaredMethod("doLock");
        int modifiers = method.getModifiers();

        assertTrue(java.lang.reflect.Modifier.isProtected(modifiers),
            "doLock should be protected");
    }

    @Test
    @DisplayName("Constructor should accept required parameters")
    void constructorHasCorrectSignature() throws NoSuchMethodException {
        var constructor = AuroraDSQLTable.class.getDeclaredConstructor(
            org.flywaydb.core.internal.jdbc.JdbcTemplate.class,
            AuroraDSQLDatabase.class,
            org.flywaydb.database.postgresql.PostgreSQLSchema.class,
            String.class
        );
        assertNotNull(constructor);
        assertTrue(java.lang.reflect.Modifier.isPublic(constructor.getModifiers()));
    }
}
