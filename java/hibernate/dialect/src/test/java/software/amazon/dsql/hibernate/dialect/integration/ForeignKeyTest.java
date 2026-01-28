// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import org.hibernate.Session;
import org.hibernate.boot.Metadata;
import org.hibernate.boot.MetadataSources;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.tool.hbm2ddl.SchemaExport;
import org.hibernate.tool.schema.TargetType;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import software.amazon.dsql.hibernate.dialect.integration.model.M2OEntityA;
import software.amazon.dsql.hibernate.dialect.integration.model.M2OEntityB;
import software.amazon.dsql.hibernate.dialect.integration.model.M2MEntityA;
import software.amazon.dsql.hibernate.dialect.integration.model.M2MEntityB;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@EnabledIfSystemProperty(named = "RUN_INTEGRATION", matches = "TRUE")
public class ForeignKeyTest extends DSQLHibernateBaseTest {

    @Test
    void testOneToManyRelationship() {
        M2OEntityB m2OEntityB = new M2OEntityB();
        m2OEntityB.setValue("Parent Entity");
        M2OEntityA m2OEntityA1 = new M2OEntityA();
        m2OEntityA1.setValue("Child Entity 1");
        M2OEntityA m2OEntityA2 = new M2OEntityA();
        m2OEntityA2.setValue("Child Entity 2");

        m2OEntityB.setEntityAs(List.of(m2OEntityA1, m2OEntityA2));

        UUID entityBId, entityA1Id, entityA2Id;

        try (Session session = getSession()) {
            session.beginTransaction();
            session.persist(m2OEntityB);
            session.persist(m2OEntityA1);
            session.persist(m2OEntityA2);
            session.getTransaction().commit();

            // Store IDs for later retrieval
            entityBId = m2OEntityB.getId();
            entityA1Id = m2OEntityA1.getId();
            entityA2Id = m2OEntityA2.getId();
        }

        try (Session session = getSession()) {
            M2OEntityB retrievedM2OEntityB = session.get(M2OEntityB.class, entityBId);
            Assertions.assertEquals("Parent Entity", retrievedM2OEntityB.getValue());

            M2OEntityA retrievedM2OEntityA1 = session.get(M2OEntityA.class, entityA1Id);
            M2OEntityA retrievedM2OEntityA2 = session.get(M2OEntityA.class, entityA2Id);
            Assertions.assertEquals("Child Entity 1", retrievedM2OEntityA1.getValue());
            Assertions.assertEquals("Child Entity 2", retrievedM2OEntityA2.getValue());

            List<M2OEntityA> retrievedChildren = retrievedM2OEntityB.getEntityAs();
            Assertions.assertEquals(2, retrievedChildren.size(), "Should have 2 child entities");

            Set<UUID> childIds = retrievedChildren.stream()
                    .map(M2OEntityA::getId)
                    .collect(Collectors.toSet());
            Assertions.assertTrue(childIds.contains(entityA1Id), "Should contain Child Entity 1");
            Assertions.assertTrue(childIds.contains(entityA2Id), "Should contain Child Entity 2");
        }
    }

    @Test
    void testManyToManyRelationship() {
        M2MEntityA entityA1 = new M2MEntityA();
        entityA1.setName("EntityA 1");
        M2MEntityA entityA2 = new M2MEntityA();
        entityA2.setName("EntityA 2");
        M2MEntityB entityB1 = new M2MEntityB();
        entityB1.setName("EntityB 1");
        M2MEntityB entityB2 = new M2MEntityB();
        entityB2.setName("EntityB 2");

        entityA1.setEntityBs(new HashSet<>(List.of(entityB1, entityB2)));
        entityA2.setEntityBs(new HashSet<>(List.of(entityB2)));
        entityB1.setEntityAs(new HashSet<>(List.of(entityA1)));
        entityB2.setEntityAs(new HashSet<>(List.of(entityA1, entityA2)));

        UUID entityA1Id, entityA2Id, entityB1Id, entityB2Id;

        try (Session session = getSession()) {
            session.beginTransaction();
            session.persist(entityA1);
            session.persist(entityA2);
            session.persist(entityB1);
            session.persist(entityB2);
            session.getTransaction().commit();

            entityA1Id = entityA1.getId();
            entityA2Id = entityA2.getId();
            entityB1Id = entityB1.getId();
            entityB2Id = entityB2.getId();
        }

        // Verify relationships
        try (Session session = getSession()) {
            M2MEntityA retrievedA1 = session.get(M2MEntityA.class, entityA1Id);
            Assertions.assertEquals(2, retrievedA1.getEntityBs().size(), "A1 should have 2 B entities");
            Assertions.assertTrue(retrievedA1.getEntityBs().stream().anyMatch(b -> b.getId().equals(entityB1Id)), "A1 should relate to B1");
            Assertions.assertTrue(retrievedA1.getEntityBs().stream().anyMatch(b -> b.getId().equals(entityB2Id)), "A1 should relate to B2");

            M2MEntityB retrievedB2 = session.get(M2MEntityB.class, entityB2Id);
            Assertions.assertEquals(2, retrievedB2.getEntityAs().size(), "B2 should have 2 A entities");
            Assertions.assertTrue(retrievedB2.getEntityAs().stream().anyMatch(a -> a.getId().equals(entityA1Id)), "B2 should relate to A1");
            Assertions.assertTrue(retrievedB2.getEntityAs().stream().anyMatch(a -> a.getId().equals(entityA2Id)), "B2 should relate to A2");
        }

        // Delete entities
        try (Session session = getSession()) {
            session.beginTransaction();
            session.createMutationQuery("delete from M2MEntityA").executeUpdate();
            session.createMutationQuery("delete from M2MEntityB").executeUpdate();
            session.getTransaction().commit();
        }

        // Verify deletion
        try (Session session = getSession()) {
            Assertions.assertNull(session.get(M2MEntityA.class, entityA1Id), "A1 should be deleted");
            Assertions.assertNull(session.get(M2MEntityA.class, entityA2Id), "A2 should be deleted");
            Assertions.assertNull(session.get(M2MEntityB.class, entityB1Id), "B1 should be deleted");
            Assertions.assertNull(session.get(M2MEntityB.class, entityB2Id), "B2 should be deleted");

            // Verify the join table is empty
            Long joinTableCount = session.createNativeQuery(
                            "SELECT COUNT(*) FROM m2m_entity_a_b", Long.class)
                    .getSingleResult();
            Assertions.assertEquals(0, joinTableCount.intValue(),
                    "Join table should be empty after entity deletion");
        }
    }

    /**
     * Tests that Hibernate does not attempt to create foreign keys when using AuroraDSQLDialect.
     * Note this test causes an exception on buildMetadata() as it is missing database info, but this exception
     * is ignored because it doesn't matter for this test, it is just testing the DDL script.
     */
    @Test
    void testDDLDoesNotCreateForeignKeys() throws IOException {
        Path scriptLocationTemp = Paths.get("schema_creation_script.sql");
        try {
            MetadataSources metadataSources = new MetadataSources(
                    new StandardServiceRegistryBuilder()
                            .applySetting("hibernate.dialect", "software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect")
                            .build());
            metadataSources.addAnnotatedClass(M2OEntityA.class);
            metadataSources.addAnnotatedClass(M2OEntityB.class);
            Metadata metadata = metadataSources.buildMetadata();

            // Generate the schema creation script
            SchemaExport schemaExport = new SchemaExport();
            schemaExport.setFormat(true);
            schemaExport.setDelimiter(";");
            schemaExport.setOutputFile("schema_creation_script.sql");
            schemaExport.createOnly(
                    EnumSet.of(TargetType.SCRIPT),
                    metadata
            );
            String script = Files.readString(scriptLocationTemp);
            boolean containsForeignKeys = script.toLowerCase().contains("foreign key");
            Assertions.assertFalse(containsForeignKeys,
                    "Schema creation attempted to create foreign keys.");
            Assertions.assertTrue(script.toLowerCase().contains("create table m2oentitya"),
                    "Script should create M2OEntityA table");
            Assertions.assertTrue(script.toLowerCase().contains("create table m2oentityb"),
                    "Script should create M2OEntityB table");
        } finally {
            Files.deleteIfExists(scriptLocationTemp);
        }
    }

    @Override
    protected List<Class<?>> getAnnotatedClasses() {
        return List.of(
                M2OEntityA.class,
                M2OEntityB.class,
                M2MEntityA.class,
                M2MEntityB.class
        );
    }
}
