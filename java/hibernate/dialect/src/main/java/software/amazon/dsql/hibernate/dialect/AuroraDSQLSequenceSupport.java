// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect;

import org.hibernate.dialect.sequence.SequenceSupport;

/**
 * Sequence support for Aurora DSQL.
 *
 * <p>Aurora DSQL requires a mandatory {@code CACHE} parameter on sequence creation. This class
 * generates the appropriate DDL for sequences with the configured cache size.
 */
public class AuroraDSQLSequenceSupport implements SequenceSupport {

  private final int sequenceCacheSize;

  public AuroraDSQLSequenceSupport(int sequenceCacheSize) {
    this.sequenceCacheSize = sequenceCacheSize;
  }

  @Override
  public String getCreateSequenceString(String sequenceName) {
    return "create sequence " + sequenceName + " cache " + sequenceCacheSize;
  }

  @Override
  public String getSelectSequenceNextValString(String sequenceName) {
    return "nextval('" + sequenceName + "')";
  }

  @Override
  public boolean sometimesNeedsStartingValue() {
    return true;
  }

  @Override
  public String getDropSequenceString(String sequenceName) {
    return "drop sequence if exists " + sequenceName;
  }
}
