package software.amazon.dsql.hibernate.dialect.integration;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import org.hibernate.Session;
import org.junit.jupiter.api.Test;
import software.amazon.dsql.hibernate.dialect.integration.model.IdentityKeyIntEntity;
import software.amazon.dsql.hibernate.dialect.integration.model.IdentityKeyLongEntity;

public class IdentityTest extends DSQLHibernateBaseTest {

  @Test
  void testLongIdentityPrimaryKey() {
    IdentityKeyLongEntity entity = new IdentityKeyLongEntity();
    entity.setName("Identity Entity 1");
    try (Session session = getSession()) {
      session.beginTransaction();
      session.persist(entity);
      session.getTransaction().commit();
    }
    try (Session session = getSession()) {
      IdentityKeyLongEntity retrievedEntity =
          session.get(IdentityKeyLongEntity.class, entity.getId());
      assertEquals("Identity Entity 1", retrievedEntity.getName());
    }
  }

  /**
   * DSQL only supports IDENTITY with bigint, so this test confirms entities with int ID handle
   * casting correctly.
   */
  @Test
  void testIntIdentityPrimaryKey() {
    IdentityKeyIntEntity entity = new IdentityKeyIntEntity();
    entity.setName("Identity Entity 1");
    try (Session session = getSession()) {
      session.beginTransaction();
      session.persist(entity);
      session.getTransaction().commit();
    }
    try (Session session = getSession()) {
      IdentityKeyIntEntity retrievedEntity =
          session.get(IdentityKeyIntEntity.class, entity.getId());
      assertEquals("Identity Entity 1", retrievedEntity.getName());
      assertEquals(entity.getId(), retrievedEntity.getId());
    }
  }

  @Override
  protected List<Class<?>> getAnnotatedClasses() {
    return List.of(IdentityKeyLongEntity.class, IdentityKeyIntEntity.class);
  }
}
