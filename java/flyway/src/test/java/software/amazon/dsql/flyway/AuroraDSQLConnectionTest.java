/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.dsql.flyway;

import org.flywaydb.core.internal.database.base.Schema;
import org.flywaydb.core.internal.database.base.Table;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import java.lang.reflect.Method;
import java.util.concurrent.Callable;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for AuroraDSQLConnection.
 *
 * <p>These tests verify method signatures and return types.
 * Basic override tests are in AuroraDSQLDatabaseTest.</p>
 */
class AuroraDSQLConnectionTest {

    @Test
    @DisplayName("getSchema() return type should be Schema")
    void getSchemaReturnType() throws NoSuchMethodException {
        Method method = AuroraDSQLConnection.class.getDeclaredMethod("getSchema", String.class);
        assertEquals(Schema.class, method.getReturnType(),
            "getSchema should return Schema");
    }

    @Test
    @DisplayName("lock() should accept Table and Callable parameters")
    void lockParameterTypes() throws NoSuchMethodException {
        Method method = AuroraDSQLConnection.class.getDeclaredMethod("lock",
            Table.class, Callable.class);
        Class<?>[] paramTypes = method.getParameterTypes();

        assertEquals(2, paramTypes.length);
        assertEquals(Table.class, paramTypes[0]);
        assertEquals(Callable.class, paramTypes[1]);
    }

    @Test
    @DisplayName("doRestoreOriginalState() should declare SQLException")
    void doRestoreOriginalStateDeclaresSqlException() throws NoSuchMethodException {
        Method method = AuroraDSQLConnection.class.getDeclaredMethod("doRestoreOriginalState");
        Class<?>[] exceptionTypes = method.getExceptionTypes();

        assertEquals(1, exceptionTypes.length);
        assertEquals(java.sql.SQLException.class, exceptionTypes[0]);
    }
}
