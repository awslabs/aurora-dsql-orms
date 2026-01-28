// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import org.hibernate.SessionFactory;
import org.hibernate.boot.MetadataSources;
import org.hibernate.boot.registry.StandardServiceRegistry;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.cfg.Configuration;
import org.hibernate.dialect.Dialect;
import org.hibernate.engine.jdbc.spi.JdbcServices;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.junit.jupiter.api.parallel.Isolated;
import software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect;

import java.util.HashMap;
import java.util.Map;

@TestInstance(TestInstance.Lifecycle.PER_METHOD)
@Isolated
@EnabledIfSystemProperty(named = "RUN_INTEGRATION", matches = "TRUE")
public class DialectConfigurationTest {

    @Test
    void testDialectWithStandardServiceRegistryBuilder() {
        Map<String, Object> settings = new HashMap<>();
        settings.put("hibernate.dialect", "software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect");
        settings.put("hibernate.connection.url", DSQLHibernateBaseTest.url);
        settings.put("hibernate.connection.username", "admin");
        settings.put("hibernate.connection.password", DSQLHibernateBaseTest.generateToken());
        settings.put("hibernate.connection.driver_class", "org.postgresql.Driver");

        StandardServiceRegistry registry = new StandardServiceRegistryBuilder()
                .applySettings(settings)
                .build();

        try (SessionFactory sessionFactory = new MetadataSources(registry).buildMetadata().buildSessionFactory()) {
            Dialect dialect = sessionFactory.getSessionFactoryOptions()
                    .getServiceRegistry()
                    .getService(JdbcServices.class)
                    .getDialect();
            Assertions.assertInstanceOf(AuroraDSQLDialect.class, dialect);
        } finally {
            StandardServiceRegistryBuilder.destroy(registry);
        }
    }

    @Test
    void testDialectWithConfigurationAPI() {
        Configuration configuration = new Configuration()
                .setProperty("hibernate.dialect", "software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect")
                .setProperty("hibernate.connection.url", DSQLHibernateBaseTest.url)
                .setProperty("hibernate.connection.username", "admin")
                .setProperty("hibernate.connection.password", DSQLHibernateBaseTest.generateToken())
                .setProperty("hibernate.connection.driver_class", "org.postgresql.Driver");

        try (SessionFactory sessionFactory = configuration.buildSessionFactory()) {
            Dialect dialect = sessionFactory.getSessionFactoryOptions()
                    .getServiceRegistry()
                    .getService(JdbcServices.class)
                    .getDialect();
            Assertions.assertInstanceOf(AuroraDSQLDialect.class, dialect);
        }
    }
}
