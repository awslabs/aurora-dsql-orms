// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration.model;

import jakarta.persistence.Column;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.MappedSuperclass;
import java.io.Serializable;
import java.util.UUID;
import org.hibernate.annotations.ColumnDefault;

@MappedSuperclass
public class BaseEntity implements Serializable {

  @Id
  @GeneratedValue
  @ColumnDefault("gen_random_uuid()")
  @Column(name = "id", updatable = false, nullable = false)
  private UUID id;

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public boolean isNew() {
    return this.id == null;
  }
}
