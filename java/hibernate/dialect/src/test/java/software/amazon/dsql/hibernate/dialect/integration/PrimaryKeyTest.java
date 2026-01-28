// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import java.util.List;
import java.util.UUID;
import org.hibernate.Session;
import org.hibernate.exception.GenericJDBCException;
import org.hibernate.id.IdentifierGenerationException;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.postgresql.util.PSQLException;
import software.amazon.dsql.hibernate.dialect.integration.model.IntegerKeyEntity;
import software.amazon.dsql.hibernate.dialect.integration.model.SequenceKeyEntity;
import software.amazon.dsql.hibernate.dialect.integration.model.SimpleEntity;

@EnabledIfSystemProperty(named = "RUN_INTEGRATION", matches = "TRUE")
public class PrimaryKeyTest extends DSQLHibernateBaseTest {

  @Test
  void testUUIDPrimaryKey() {
    SimpleEntity entity = new SimpleEntity();
    entity.setName("UUID Test Entity");
    entity.setValue(100);
    UUID entityId;
    try (Session session = getSession()) {
      session.beginTransaction();
      session.persist(entity);
      session.getTransaction().commit();
      entityId = entity.getId();
      Assertions.assertNotNull(entityId, "UUID should be generated");
    }

    // Retrieve/query by UUID
    try (Session session = getSession()) {
      SimpleEntity retrievedEntity = session.get(SimpleEntity.class, entityId);
      Assertions.assertNotNull(retrievedEntity, "Entity should be retrievable by UUID");
      Assertions.assertEquals("UUID Test Entity", retrievedEntity.getName());
      Assertions.assertEquals(100, retrievedEntity.getValue());
    }
    try (Session session = getSession()) {
      SimpleEntity queriedEntity =
          session
              .createQuery("FROM SimpleEntity WHERE id = :id", SimpleEntity.class)
              .setParameter("id", entityId)
              .uniqueResult();
      Assertions.assertNotNull(queriedEntity, "Entity should be queryable by UUID");
      Assertions.assertEquals("UUID Test Entity", queriedEntity.getName());
    }

    // Update entity by UUID
    try (Session session = getSession()) {
      session.beginTransaction();
      SimpleEntity entityToUpdate = session.get(SimpleEntity.class, entityId);
      entityToUpdate.setName("Updated UUID Entity");
      session.getTransaction().commit();
    }

    try (Session session = getSession()) {
      SimpleEntity updatedEntity = session.get(SimpleEntity.class, entityId);
      Assertions.assertEquals("Updated UUID Entity", updatedEntity.getName());
    }

    // Delete by UUID
    try (Session session = getSession()) {
      session.beginTransaction();

      SimpleEntity entityToDelete = session.get(SimpleEntity.class, entityId);
      session.remove(entityToDelete);

      session.getTransaction().commit();
    }
    try (Session session = getSession()) {
      SimpleEntity deletedEntity = session.get(SimpleEntity.class, entityId);
      Assertions.assertNull(deletedEntity, "Entity should be deletable by UUID");
    }
  }

  @Test
  void testIntegerPrimaryKey() {
    IntegerKeyEntity entity1 = new IntegerKeyEntity();
    entity1.setName("Integer Entity 1");
    entity1.setId(1);
    IntegerKeyEntity entity2 = new IntegerKeyEntity();
    entity2.setName("Integer Entity 2");
    entity2.setId(2);

    try (Session session = getSession()) {
      session.beginTransaction();
      session.persist(entity1);
      session.persist(entity2);
      session.getTransaction().commit();
    }

    try (Session session = getSession()) {
      IntegerKeyEntity retrievedEntity1 = session.get(IntegerKeyEntity.class, 1);
      Assertions.assertEquals("Integer Entity 1", retrievedEntity1.getName());
      IntegerKeyEntity retrievedEntity2 = session.get(IntegerKeyEntity.class, 2);
      Assertions.assertEquals("Integer Entity 2", retrievedEntity2.getName());
    }

    IntegerKeyEntity entityMissingKey = new IntegerKeyEntity();
    entityMissingKey.setName("Integer Entity 3");
    try (Session session = getSession()) {
      session.beginTransaction();
      session.persist(entityMissingKey);
      session.getTransaction().commit();
    } catch (IdentifierGenerationException e) {
      // Expected
    }
  }

  /** Should fail to create, as auto-incrementing values aren't supported. */
  @Test
  void testSequencePrimaryKey() {
    SequenceKeyEntity entity = new SequenceKeyEntity();
    entity.setName("Sequence Entity 1");
    try (Session session = getSession()) {
      session.beginTransaction();
      session.persist(entity);
      session.getTransaction().commit();
    } catch (GenericJDBCException e) {
      Assertions.assertInstanceOf(PSQLException.class, e.getCause());
    }
  }

  @Override
  protected List<Class<?>> getAnnotatedClasses() {
    return List.of(SimpleEntity.class, SequenceKeyEntity.class, IntegerKeyEntity.class);
  }
}
