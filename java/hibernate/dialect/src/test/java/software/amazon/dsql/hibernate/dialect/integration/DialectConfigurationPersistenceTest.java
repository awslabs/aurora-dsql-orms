// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import static software.amazon.dsql.hibernate.dialect.integration.DSQLHibernateBaseTest.generateToken;

import jakarta.persistence.EntityManager;
import jakarta.persistence.EntityManagerFactory;
import jakarta.persistence.Persistence;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.dialect.Dialect;
import org.hibernate.engine.jdbc.spi.JdbcServices;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.junit.jupiter.api.parallel.Isolated;
import software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect;

@EnabledIfSystemProperty(named = "RUN_INTEGRATION", matches = "TRUE")
@Isolated
public class DialectConfigurationPersistenceTest {

  @Test
  void testDialectFromPersistenceXml() throws IOException {
    // Places the persistence.xml in build/resources/test/META-INF as this is where JPA expects it
    File metaInfDir = new File(System.getProperty("test.resources.dir") + "/META-INF");
    metaInfDir.mkdirs();
    File persistenceXml = new File(metaInfDir, "persistence.xml");
    String token = generateToken();
    String escapedToken = token.replace("&", "&amp;");
    String escapedUrl = DSQLHibernateBaseTest.url.replace("&", "&amp;");
    try (FileWriter writer = new FileWriter(persistenceXml)) {
      writer.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
      writer.write("<persistence xmlns=\"http://xmlns.jcp.org/xml/ns/persistence\"\n");
      writer.write("             xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n");
      writer.write("             xsi:schemaLocation=\"http://xmlns.jcp.org/xml/ns/persistence\n");
      writer.write("             http://xmlns.jcp.org/xml/ns/persistence/persistence_2_2.xsd\"\n");
      writer.write("             version=\"2.2\">\n");
      writer.write(
          "    <persistence-unit name=\"testPersistence\" transaction-type=\"RESOURCE_LOCAL\">\n");
      writer.write("        <provider>org.hibernate.jpa.HibernatePersistenceProvider</provider>\n");
      writer.write("        <properties>\n");
      writer.write(
          "            <property name=\"hibernate.dialect\""
              + " value=\"software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect\"/>\n");
      writer.write(
          "            <property name=\"javax.persistence.jdbc.url\" value=\""
              + escapedUrl
              + "\"/>\n");
      writer.write(
          "            <property name=\"javax.persistence.jdbc.user\" value=\"admin\"/>\n");
      writer.write(
          "            <property name=\"javax.persistence.jdbc.password\" value=\""
              + escapedToken
              + "\"/>\n");
      writer.write(
          "            <property name=\"javax.persistence.jdbc.driver\""
              + " value=\"org.postgresql.Driver\"/>\n");
      writer.write("        </properties>\n");
      writer.write("    </persistence-unit>\n");
      writer.write("</persistence>\n");
      writer.flush();
    }

    try (EntityManagerFactory emf = Persistence.createEntityManagerFactory("testPersistence");
        EntityManager em = emf.createEntityManager();
        Session session = em.unwrap(Session.class);
        SessionFactory sessionFactory = session.getSessionFactory(); ) {
      Dialect dialect =
          sessionFactory
              .getSessionFactoryOptions()
              .getServiceRegistry()
              .getService(JdbcServices.class)
              .getDialect();
      Assertions.assertInstanceOf(AuroraDSQLDialect.class, dialect);
    } finally {
      if (persistenceXml.exists()) {
        persistenceXml.delete();
      }
      if (metaInfDir.exists()) {
        metaInfDir.delete();
      }
    }
  }
}
