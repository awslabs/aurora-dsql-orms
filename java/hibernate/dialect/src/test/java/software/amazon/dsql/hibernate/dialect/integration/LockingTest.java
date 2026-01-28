// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import static jakarta.persistence.LockModeType.PESSIMISTIC_WRITE;
import static org.junit.jupiter.api.Assertions.fail;

import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.hibernate.LockMode;
import org.hibernate.Session;
import org.hibernate.query.Query;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import software.amazon.dsql.hibernate.dialect.integration.model.SimpleEntity;
import software.amazon.dsql.hibernate.dialect.integration.model.VersionedEntity;

@EnabledIfSystemProperty(named = "RUN_INTEGRATION", matches = "TRUE")
public class LockingTest extends DSQLHibernateBaseTest {

  @Test
  void testOptimisticLockingFailure() throws InterruptedException {
    UUID entityId;
    try (Session session = getSession()) {
      session.beginTransaction();
      VersionedEntity entity = new VersionedEntity();
      entity.setName("Initial Name");
      session.persist(entity);
      session.getTransaction().commit();
      entityId = entity.getId();
    }
    try (Session session = getSession()) {
      VersionedEntity entity = session.get(VersionedEntity.class, entityId);
      Assertions.assertEquals(0, entity.getVersion());
      Assertions.assertEquals("Initial Name", entity.getName());
    }
    final CountDownLatch firstTransactionStarted = new CountDownLatch(1);
    final CountDownLatch secondTransactionReady = new CountDownLatch(1);
    final CountDownLatch optimisticLockExceptionOccurred = new CountDownLatch(1);
    ExecutorService executor = Executors.newFixedThreadPool(2);

    // First transaction - will succeed
    executor.submit(
        () -> {
          try (Session session = getSession()) {
            session.beginTransaction();
            VersionedEntity entity = session.get(VersionedEntity.class, entityId);
            entity.setName("Updated by Transaction 1");

            // Signal that first transaction has started
            firstTransactionStarted.countDown();

            // Wait for second transaction to be ready
            secondTransactionReady.await();
            // Commit the first transaction
            session.getTransaction().commit();
          } catch (Exception e) {
            e.printStackTrace();
          }
        });
    // Second transaction - will fail with optimistic lock exception
    executor.submit(
        () -> {
          try {
            firstTransactionStarted.await();
            try (Session session = getSession()) {
              session.beginTransaction();
              VersionedEntity entity = session.get(VersionedEntity.class, entityId);
              entity.setName("Updated by Transaction 2");
              secondTransactionReady.countDown();
              Thread.sleep(1000);
              // Sleep to ensure second transaction attempts to commit first
              // Try to commit - should fail with optimistic lock exception
              session.getTransaction().commit();
            }
          } catch (Exception e) {
            if (e.getMessage().contains("OC000") || e.getCause().getMessage().contains("OC000")) {
              optimisticLockExceptionOccurred.countDown();
            }
          }
        });
    executor.shutdown();
    executor.awaitTermination(10, TimeUnit.SECONDS);
    Assertions.assertTrue(
        optimisticLockExceptionOccurred.await(0, TimeUnit.SECONDS),
        "Expected optimistic locking exception did not occur");

    // Verify final state - first transaction should have succeeded
    try (Session session = getSession()) {
      VersionedEntity entity = session.get(VersionedEntity.class, entityId);
      Assertions.assertEquals(1, entity.getVersion());
      Assertions.assertEquals("Updated by Transaction 1", entity.getName());
    }
  }

  @Test
  void testPessimisticLockWithQuery() {
    UUID entityId;
    try (Session session = getSession()) {
      session.beginTransaction();
      SimpleEntity entity = new SimpleEntity();
      entity.setName("Query Test Entity");
      session.persist(entity);
      session.getTransaction().commit();
      entityId = entity.getId();
    }
    try (Session session = getSession()) {
      session.beginTransaction();
      Query<SimpleEntity> query =
          session
              .createQuery("FROM SimpleEntity e WHERE e.id = :id", SimpleEntity.class)
              .setParameter("id", entityId)
              .setLockMode(PESSIMISTIC_WRITE);
      SimpleEntity entity = query.getSingleResult();
      Assertions.assertNotNull(entity);
      entity.setName("Updated via Query with FOR UPDATE");
      session.getTransaction().commit();
    }
    try (Session session = getSession()) {
      SimpleEntity entity = session.get(SimpleEntity.class, entityId);
      Assertions.assertEquals("Updated via Query with FOR UPDATE", entity.getName());
    }
  }

  /**
   * This test verifies that FOR UPDATE works with Hibernate's pessimistic locking. In this
   * scenario, a first transaction reads a value in entity 1 with SELECT FOR UPDATE, then attempts
   * to write that value to entity 2. This should fail however because entity 1 was modified by a
   * second transaction in between the read and write.
   */
  @Test
  void testForUpdateWithConcurrentTransactions() throws Exception {

    UUID entityId1, entityId2;
    ;
    try (Session session = getSession()) {
      SimpleEntity entity1 = new SimpleEntity();
      entity1.setName("Concurrent Test Entity 1");
      entity1.setValue(1);
      SimpleEntity entity2 = new SimpleEntity();
      entity2.setName("Concurrent Test Entity 2");
      entity2.setValue(2);
      session.beginTransaction();
      session.persist(entity1);
      session.persist(entity2);
      session.getTransaction().commit();
      entityId1 = entity1.getId();
      entityId2 = entity2.getId();
    }
    final CountDownLatch transaction1ReadComplete = new CountDownLatch(1);
    final CountDownLatch transaction2CommitComplete = new CountDownLatch(1);
    ExecutorService executor = Executors.newFixedThreadPool(2);

    // Transaction 1 - Reads entity 1 with FOR UPDATE then tries to update entity 2 but fails
    executor.submit(
        () -> {
          try (Session session = getSession()) {
            session.beginTransaction();
            SimpleEntity readEntity1 =
                session.get(
                    SimpleEntity.class, entityId1, LockMode.PESSIMISTIC_WRITE // Adds FOR UPDATE
                    );
            int originalValue = readEntity1.getValue();
            transaction1ReadComplete.countDown();
            // Wait for transaction 2 to modify and commit entity1
            transaction2CommitComplete.await(5, TimeUnit.SECONDS);

            SimpleEntity entity2ToUpdate = session.get(SimpleEntity.class, entityId2);
            entity2ToUpdate.setValue(originalValue); // Using stale value from entity1
            session.getTransaction().commit();
            fail("Should have failed with OC000");
          } catch (Exception e) {
            Assertions.assertTrue(e.getMessage().contains("OC000"), e.getMessage());
          }
        });

    // Transaction 2: Modify and commit entity1
    executor.submit(
        () -> {
          try (Session session = getSession()) {
            session.beginTransaction();
            // Wait for transaction 1 to read entity1
            transaction1ReadComplete.await(5, TimeUnit.SECONDS);
            SimpleEntity entity1ToUpdate = session.get(SimpleEntity.class, entityId1);
            entity1ToUpdate.setValue(2);
            session.getTransaction().commit();
            transaction2CommitComplete.countDown();
          } catch (Exception e) {
            throw new RuntimeException(e);
          }
        });
    executor.shutdown();
    boolean completed = executor.awaitTermination(10, TimeUnit.SECONDS);
    Assertions.assertTrue(completed, "Test timed out");
    // Verify end result
    try (Session session = getSession()) {
      SimpleEntity finalEntity1 = session.get(SimpleEntity.class, entityId1);
      SimpleEntity finalEntity2 = session.get(SimpleEntity.class, entityId2);

      Assertions.assertEquals(
          2, finalEntity1.getValue(), "Entity1 value should reflect transaction 2's update");
      Assertions.assertEquals(2, finalEntity2.getValue(), "Entity2 value should remain unchanged");
    }
  }

  @Override
  protected List<Class<?>> getAnnotatedClasses() {
    return List.of(SimpleEntity.class, VersionedEntity.class);
  }
}
