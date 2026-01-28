// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToMany;

import java.util.ArrayList;
import java.util.List;

@Entity
public class M2OEntityB extends BaseEntity {

    @Column(name = "val")
    private String value;

    @OneToMany
    @JoinColumn(name = "entity_b_id")
    private List<M2OEntityA> m2OEntityAS = new ArrayList<>();

    public String getValue() {
        return this.value;
    }

    public void setValue(String value) {
        this.value = value;
    }

    public List<M2OEntityA> getEntityAs() {
        return m2OEntityAS;
    }

    public void setEntityAs(List<M2OEntityA> m2OEntityAS) {
        this.m2OEntityAS = m2OEntityAS;
    }
}
