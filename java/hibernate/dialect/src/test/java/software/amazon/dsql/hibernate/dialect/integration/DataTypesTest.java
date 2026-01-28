// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Date;
import java.util.List;
import java.util.UUID;
import org.hibernate.Session;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import software.amazon.dsql.hibernate.dialect.integration.model.DataTypesEntity;

/**
 * Tests that various data types are handled correctly by the dialect, especially numeric
 * precisions.
 */
@EnabledIfSystemProperty(named = "RUN_INTEGRATION", matches = "TRUE")
public class DataTypesTest extends DSQLHibernateBaseTest {

  @Test
  void testAllTypes() {
    DataTypesEntity entity = new DataTypesEntity();
    entity.setFloatVal(123.456789f);
    entity.setDoubleVal(987.654321d);
    entity.setDecimalVal(new BigDecimal("123456.789012"));
    entity.setBinaryVal("binary data test".getBytes());
    entity.setDateVal(new Date());

    UUID entityId;
    try (Session session = getSession()) {
      session.beginTransaction();
      session.persist(entity);
      session.flush();
      session.getTransaction().commit();
      entityId = entity.getId();
    }

    try (Session session = getSession()) {
      DataTypesEntity retrievedEntity = session.get(DataTypesEntity.class, entityId);

      Assertions.assertNotNull(retrievedEntity);
      Assertions.assertEquals(entity.getFloatVal(), retrievedEntity.getFloatVal());
      Assertions.assertEquals(entity.getDoubleVal(), retrievedEntity.getDoubleVal());
      Assertions.assertEquals(
          entity.getDecimalVal().toString(), retrievedEntity.getDecimalVal().toString());
      Assertions.assertArrayEquals(entity.getBinaryVal(), retrievedEntity.getBinaryVal());
      Assertions.assertEquals(
          entity.getDateVal().getTime(), retrievedEntity.getDateVal().getTime());
    }
  }

  @Test
  void testNumericPrecision() {
    BigDecimal[] testValues = {
      new BigDecimal("0.1"),
      new BigDecimal("0.12"),
      new BigDecimal("0.12345678"),
      new BigDecimal("9999999.999999")
    };

    UUID[] entityIds = new UUID[testValues.length];

    try (Session session = getSession()) {
      session.beginTransaction();
      for (int i = 0; i < testValues.length; i++) {
        DataTypesEntity entity = new DataTypesEntity();
        entity.setDecimalValDefault(testValues[i]);
        session.persist(entity);
        entityIds[i] = entity.getId();
      }
      session.getTransaction().commit();
    }

    try (Session session = getSession()) {
      for (int i = 0; i < entityIds.length; i++) {
        DataTypesEntity entity = session.get(DataTypesEntity.class, entityIds[i]);
        // Assert that values are truncated to 2 decimal places
        BigDecimal expected = testValues[i].setScale(2, RoundingMode.HALF_UP);
        Assertions.assertEquals(
            expected.compareTo(entity.getDecimalValDefault()),
            0,
            "Value should be stored with 2 decimal places");
      }

      Object[] columnInfo =
          session
              .createNativeQuery(
                  "SELECT column_name, data_type, numeric_precision, numeric_scale FROM"
                      + " information_schema.columns WHERE table_name = 'datatypesentity' AND"
                      + " column_name = 'decimalvaldefault'",
                  Object[].class)
              .getSingleResult();
      Assertions.assertEquals(
          "numeric", columnInfo[1].toString().toLowerCase(), "Data type should be numeric");
      Integer precision = Integer.valueOf(columnInfo[2].toString());
      Assertions.assertEquals(18, precision, "Precision should be 18");
      Integer scale = Integer.valueOf(columnInfo[3].toString());
      Assertions.assertEquals(2, scale, "Scale should be 2");
    }
  }

  @Test
  void testFloatDoublePrecision() {
    float[] floatValues = {123.456789f, 0.123456f, 9999999.999999f};

    double[] doubleValues = {123.456789012345, 0.123456789012345, 9999999.999999999999};

    UUID[] entityIds = new UUID[floatValues.length];
    try (Session session = getSession()) {
      session.beginTransaction();
      for (int i = 0; i < floatValues.length; i++) {
        DataTypesEntity entity = new DataTypesEntity();
        entity.setFloatVal(floatValues[i]);
        entity.setDoubleVal(doubleValues[i]);
        session.persist(entity);
        entityIds[i] = entity.getId();
      }
      session.getTransaction().commit();
    }

    try (Session session = getSession()) {
      for (int i = 0; i < entityIds.length; i++) {
        DataTypesEntity entity = session.get(DataTypesEntity.class, entityIds[i]);
        float expectedFloat = floatValues[i];
        Assertions.assertEquals(expectedFloat, entity.getFloatVal(), 0.0001f);

        double expectedDouble = doubleValues[i];
        Assertions.assertEquals(expectedDouble, entity.getDoubleVal(), 0.000000000001);
      }

      List<Object[]> columnInfo =
          session
              .createNativeQuery(
                  "SELECT column_name, data_type, numeric_precision, numeric_scale FROM"
                      + " information_schema.columns WHERE table_name = 'datatypesentity' AND"
                      + " (column_name = 'floatval' OR column_name = 'doubleval')ORDER BY"
                      + " column_name",
                  Object[].class)
              .getResultList();

      Object[] doubleInfo = columnInfo.get(0);
      Assertions.assertEquals(
          "doubleval", doubleInfo[0].toString().toLowerCase(), "First column should be doubleVal");
      Assertions.assertEquals(
          "double precision",
          doubleInfo[1].toString().toLowerCase(),
          "Type should be double precision");
      Assertions.assertEquals(
          53, Integer.valueOf(doubleInfo[2].toString()), "Double precision should be 52 in DSQL");
      Object[] floatInfo = columnInfo.get(1);
      Assertions.assertEquals(
          "floatval", floatInfo[0].toString().toLowerCase(), "Second column should be floatVal");
      Assertions.assertEquals("real", floatInfo[1].toString().toLowerCase(), "Type should be real");
      Assertions.assertEquals(
          24, Integer.valueOf(floatInfo[2].toString()), "Float precision should be 24 in DSQL");
    }
  }

  @Override
  protected List<Class<?>> getAnnotatedClasses() {
    return List.of(DataTypesEntity.class);
  }
}
