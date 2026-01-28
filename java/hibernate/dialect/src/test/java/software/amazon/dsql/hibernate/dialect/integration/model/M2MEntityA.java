// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;

import java.util.HashSet;
import java.util.Set;

@Entity
public class M2MEntityA extends BaseEntity {

    @Column(name = "name")
    private String name;

    @ManyToMany
    @JoinTable(
            name = "m2m_entity_a_b",
            joinColumns = @JoinColumn(name = "entity_a_id"),
            inverseJoinColumns = @JoinColumn(name = "entity_b_id")
    )
    private Set<M2MEntityB> entityBs = new HashSet<>();

    public String getName() {
        return name;
    }

    public void setName(String title) {
        this.name = title;
    }

    public Set<M2MEntityB> getEntityBs() {
        return entityBs;
    }

    public void setEntityBs(Set<M2MEntityB> entityBs) {
        this.entityBs = entityBs;
    }
}
