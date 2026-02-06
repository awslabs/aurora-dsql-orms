// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import org.hibernate.Session;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect;
import software.amazon.dsql.hibernate.dialect.integration.model.IdentityKeyLongEntity;
import software.amazon.dsql.hibernate.dialect.integration.model.SequenceKeyEntity;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.fail;

@EnabledIfSystemProperty(named = "RUN_INTEGRATION", matches = "TRUE")
public class SequenceIdentityCacheTest extends DSQLHibernateBaseTest {

    @Test
    void testSequenceCache1() {
        try (Session session = getSession()) {
            String sql = "SELECT s.seqcache FROM pg_sequence s " +
                    "JOIN pg_class c ON s.seqrelid = c.oid " +
                    "WHERE c.relname = 'sequencekeyentity_seq'";
            Long cacheSize = (Long) session.createNativeQuery(sql, Long.class).getSingleResult();
            assertEquals(1L, cacheSize, "Sequence cache should be 1");
        }
    }

    @Test
    void testIdentityCache1() {
        try (Session session = getSession()) {
            String sql = "SELECT s.seqcache FROM pg_sequence s " +
                    "JOIN pg_class c ON s.seqrelid = c.oid " +
                    "WHERE c.relname LIKE 'identitykeylongentity_id_seq%'";
            Long cacheSize = (Long) session.createNativeQuery(sql, Long.class).getSingleResult();
            assertEquals(1L, cacheSize, "Identity sequence cache should be 1");
        }
    }

    @BeforeEach
    public void beforeEach() {
        this.configuration = createConfiguration();
        this.configuration.setProperty(AuroraDSQLDialect.SEQUENCE_CACHE_SIZE, "1");
        getAnnotatedClasses().forEach(configuration::addAnnotatedClass);
        this.sessionFactory = configuration.buildSessionFactory();
    }

    @Override
    protected List<Class<?>> getAnnotatedClasses() {
        return List.of(SequenceKeyEntity.class, IdentityKeyLongEntity.class);
    }

}