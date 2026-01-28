// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;

@Entity
public class M2OEntityA extends BaseEntity {

  @Column(name = "val")
  private String value;

  @ManyToOne
  @JoinColumn(name = "entity_b_id")
  private M2OEntityB m2OEntityB;

  public String getValue() {
    return this.value;
  }

  public void setValue(String value) {
    this.value = value;
  }

  public M2OEntityB getEntityB() {
    return m2OEntityB;
  }

  public void setEntityB(M2OEntityB m2OEntityB) {
    this.m2OEntityB = m2OEntityB;
  }
}
