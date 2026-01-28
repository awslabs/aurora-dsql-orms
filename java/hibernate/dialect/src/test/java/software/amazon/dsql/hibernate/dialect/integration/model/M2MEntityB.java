// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.ManyToMany;

import java.util.HashSet;
import java.util.Set;

@Entity
public class M2MEntityB extends BaseEntity {

    @Column(name = "name")
    private String name;

    @ManyToMany(mappedBy = "entityBs")
    private Set<M2MEntityA> entityAs = new HashSet<>();

    public String getName() {
        return name;
    }

    public void setName(String title) {
        this.name = title;
    }

    public Set<M2MEntityA> getEntityAs() {
        return entityAs;
    }

    public void setEntityAs(Set<M2MEntityA> entityAs) {
        this.entityAs = entityAs;
    }
}
