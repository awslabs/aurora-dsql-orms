// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import java.math.BigDecimal;
import java.util.Date;

@Entity
public class DataTypesEntity extends BaseEntity {

  @Column(name = "floatVal")
  private Float floatVal;

  @Column(name = "doubleVal")
  private Double doubleVal;

  @Column(name = "decimalVal", precision = 18, scale = 6)
  private BigDecimal decimalVal;

  @Column(name = "decimalValDefault")
  private BigDecimal decimalValDefault;

  @Column(name = "binaryVal")
  private byte[] binaryVal;

  @Column(name = "dateVal")
  private Date dateVal;

  public Float getFloatVal() {
    return floatVal;
  }

  public void setFloatVal(Float value) {
    this.floatVal = value;
  }

  public Double getDoubleVal() {
    return doubleVal;
  }

  public void setDoubleVal(Double doubleVal) {
    this.doubleVal = doubleVal;
  }

  public BigDecimal getDecimalVal() {
    return decimalVal;
  }

  public void setDecimalVal(BigDecimal decimalVal) {
    this.decimalVal = decimalVal;
  }

  public byte[] getBinaryVal() {
    return binaryVal;
  }

  public void setBinaryVal(byte[] binaryVal) {
    this.binaryVal = binaryVal;
  }

  public Date getDateVal() {
    return dateVal;
  }

  public void setDateVal(Date dateVal) {
    this.dateVal = dateVal;
  }

  public BigDecimal getDecimalValDefault() {
    return decimalValDefault;
  }

  public void setDecimalValDefault(BigDecimal decimalValDefault) {
    this.decimalValDefault = decimalValDefault;
  }
}
