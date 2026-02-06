// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect;

import static org.junit.jupiter.api.Assertions.*;

import org.hibernate.LockMode;
import org.hibernate.LockOptions;
import org.hibernate.dialect.identity.IdentityColumnSupport;
import org.hibernate.dialect.sequence.NoSequenceSupport;
import org.hibernate.dialect.sequence.SequenceSupport;
import org.hibernate.mapping.ForeignKey;
import org.hibernate.tool.schema.spi.Exporter;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** Unit tests for {@link AuroraDSQLDialect}. */
public class AuroraDSQLDialectTest {

  private AuroraDSQLDialect dialect;

  @BeforeEach
  public void setUp() {
    dialect = new AuroraDSQLDialect();
  }

  @Test
  public void testIdentityColumnSupport() {
    IdentityColumnSupport identityColumnSupport = dialect.getIdentityColumnSupport();
    assertNotNull(identityColumnSupport);
    assertTrue(identityColumnSupport.supportsIdentityColumns());
  }

  @Test
  public void testSequenceSupport() {
    SequenceSupport sequenceSupport = dialect.getSequenceSupport();
    assertNotNull(sequenceSupport);
    assertTrue(sequenceSupport.supportsSequences());
  }

  @Test
  public void testTemporaryTableSupport() {
    assertFalse(dialect.supportsTemporaryTables());
    assertFalse(dialect.supportsTemporaryTablePrimaryKey());
  }

  @Test
  public void testForeignKeySupport() {
    Exporter<ForeignKey> exporter = dialect.getForeignKeyExporter();
    assertNotNull(exporter);
    assertFalse(dialect.supportsCascadeDelete());
    assertFalse(dialect.dropConstraints());
  }

  @Test
  public void testLockingSupport() {
    assertFalse(dialect.supportsLockTimeouts());

    assertEquals(" for update", dialect.getForUpdateString(null, new LockOptions()));
    assertEquals(" for update", dialect.getWriteLockString(0));
    assertEquals(" for update", dialect.getWriteLockString("alias", 0));

    assertNotNull(dialect.getLockingStrategy(null, LockMode.OPTIMISTIC));
  }

  @Test
  public void testCreateIndexString() {
    assertEquals("create index async", dialect.getCreateIndexString(false));
    assertEquals("create unique index async", dialect.getCreateIndexString(true));
  }

  @Test
  public void testTruncateTableStatement() {
    assertEquals("delete from test_table", dialect.getTruncateTableStatement("test_table"));
  }

  @Test
  public void testColumnCheck() {
    assertFalse(dialect.supportsColumnCheck());
  }

  @Test
  public void testAlterColumnType() {
    assertFalse(dialect.supportsAlterColumnType());
  }

  @Test
  public void testDefaultDecimalPrecision() {
    assertEquals(18, dialect.getDefaultDecimalPrecision());
  }

  @Test
  public void testFloatPrecision() {
    assertEquals(6, dialect.getFloatPrecision());
  }

  @Test
  public void testDoublePrecision() {
    assertEquals(15, dialect.getDoublePrecision());
  }

  @Test
  public void testVarcharCapacity() {
    assertEquals(65_535, dialect.getMaxVarcharCapacity());
    assertEquals(65_535, dialect.getMaxVarcharLength());
  }

  @Test
  public void testSupportsFunctions() {
    // Test various PostgreSQL-compatible functions
    assertTrue(dialect.supportsCaseInsensitiveLike());
    assertTrue(dialect.supportsCommentOn());
    assertTrue(dialect.supportsCurrentTimestampSelection());
    assertTrue(dialect.supportsDistinctFromPredicate());
    assertTrue(dialect.supportsLateral());
    assertTrue(dialect.supportsTupleCounts());
    assertTrue(dialect.supportsValuesList());
    assertTrue(dialect.supportsWindowFunctions());
  }

  @Test
  public void testSupportsIfExists() {
    assertTrue(dialect.supportsIfExistsAfterAlterTable());
    assertTrue(dialect.supportsIfExistsBeforeConstraintName());
    assertTrue(dialect.supportsIfExistsBeforeTableName());
    assertTrue(dialect.supportsIfExistsBeforeTypeName());
  }

  @Test
  public void testGetCaseInsensitiveLike() {
    assertEquals("ilike", dialect.getCaseInsensitiveLike());
  }

  @Test
  public void testGetCurrentSchemaCommand() {
    assertEquals("select current_schema()", dialect.getCurrentSchemaCommand());
  }

  @Test
  public void testGetCurrentTimestampSelectString() {
    assertEquals("select now()", dialect.getCurrentTimestampSelectString());
    assertFalse(dialect.isCurrentTimestampSelectStringCallable());
  }

  @Test
  public void testGetCascadeConstraintsString() {
    assertEquals(" cascade", dialect.getCascadeConstraintsString());
  }

  @Test
  public void testCurrentTimeFunctions() {
    assertEquals("localtime", dialect.currentTime());
    assertEquals("localtimestamp", dialect.currentTimestamp());
    assertEquals("current_timestamp", dialect.currentTimestampWithTimeZone());
  }
}
