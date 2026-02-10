// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import java.util.List;
import org.hibernate.Session;
import org.junit.jupiter.api.Test;
import software.amazon.dsql.hibernate.dialect.integration.model.SequenceKeyEntity;
import software.amazon.dsql.hibernate.dialect.integration.model.SequenceKeyWithOptionsEntity;

public class SequenceTest extends DSQLHibernateBaseTest {

  @Test
  void testSequencePrimaryKey() {
    SequenceKeyEntity entity = new SequenceKeyEntity();
    entity.setName("Sequence Entity 1");
    try (Session session = getSession()) {
      session.beginTransaction();
      session.persist(entity);
      session.getTransaction().commit();
    }
    try (Session session = getSession()) {
      SequenceKeyEntity retrievedEntity = session.get(SequenceKeyEntity.class, entity.getId());
      assertEquals("Sequence Entity 1", retrievedEntity.getName());
    }
  }

  @Test
  void testSequenceKeyWithOptions() {
    SequenceKeyWithOptionsEntity entity = new SequenceKeyWithOptionsEntity();
    entity.setName("Sequence Entity with Options");
    SequenceKeyWithOptionsEntity entity2 = new SequenceKeyWithOptionsEntity();
    entity2.setName("Second Entity");
    try (Session session = getSession()) {
      session.beginTransaction();
      session.persist(entity);
      session.getTransaction().commit();

      session.beginTransaction();
      session.persist(entity2);
      session.getTransaction().commit();
    }
    assertNotNull(entity.getId());
    assertEquals(entity.getId() + 1, entity2.getId());
  }

  @Override
  protected List<Class<?>> getAnnotatedClasses() {
    return List.of(SequenceKeyEntity.class, SequenceKeyWithOptionsEntity.class);
  }
}
