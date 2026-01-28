// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import org.hibernate.SessionFactory;
import org.hibernate.cfg.Configuration;
import org.hibernate.dialect.Dialect;
import org.hibernate.engine.jdbc.spi.JdbcServices;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.junit.jupiter.api.parallel.Isolated;
import software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

@EnabledIfSystemProperty(named = "RUN_INTEGRATION", matches = "TRUE")
@Isolated
public class DialectConfigurationPropertiesFileTest {

    @Test
    void testDialectFromPropertiesFile() throws IOException {
        File propertiesFile = new File(System.getProperty("test.resources.dir"), "hibernate.properties");
        try (FileWriter writer = new FileWriter(propertiesFile)) {
            writer.write("hibernate.dialect=software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect\n");
            writer.write("hibernate.connection.url=" + DSQLHibernateBaseTest.url + "\n");
            writer.write("hibernate.connection.username=admin\n");
            writer.write("hibernate.connection.password=" + DSQLHibernateBaseTest.generateToken() + "\n");
            writer.write("hibernate.connection.driver_class=org.postgresql.Driver\n");
            writer.flush();
        }

        Configuration cfg = new Configuration();

        try (SessionFactory sessionFactory = cfg.buildSessionFactory();) {
            Dialect dialect = sessionFactory.getSessionFactoryOptions()
                    .getServiceRegistry()
                    .getService(JdbcServices.class)
                    .getDialect();
            Assertions.assertInstanceOf(AuroraDSQLDialect.class, dialect);
        } finally {
            // Delete the properties file after test so other tests don't use it
            if (propertiesFile.exists()) {
                propertiesFile.delete();
            }
        }
    }
}
