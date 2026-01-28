// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import org.hibernate.Session;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;

@EnabledIfSystemProperty(named = "RUN_INTEGRATION", matches = "TRUE")
public class BasicConnectionTest extends DSQLHibernateBaseTest {

    @Test
    void testBasicConnection() {
        try (Session session = getSession()) {
            Assertions.assertEquals(1, session.createQuery("SELECT 1", Integer.class).uniqueResult());
        }
    }
}
