/*
 * Copyright 2012-2026 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.samples.petclinic.model;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Collections;
import java.util.EnumSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.hibernate.boot.Metadata;
import org.hibernate.boot.MetadataSources;
import org.hibernate.boot.registry.StandardServiceRegistry;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.tool.schema.SourceType;
import org.hibernate.tool.schema.TargetType;
import org.hibernate.tool.schema.internal.ExceptionHandlerHaltImpl;
import org.hibernate.tool.schema.spi.ContributableMatcher;
import org.hibernate.tool.schema.spi.ExceptionHandler;
import org.hibernate.tool.schema.spi.ExecutionOptions;
import org.hibernate.tool.schema.spi.SchemaManagementTool;
import org.hibernate.tool.schema.spi.ScriptSourceInput;
import org.hibernate.tool.schema.spi.ScriptTargetOutput;
import org.hibernate.tool.schema.spi.SourceDescriptor;
import org.hibernate.tool.schema.spi.TargetDescriptor;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.samples.petclinic.Specialty.Specialty;
import org.springframework.samples.petclinic.owner.Owner;
import org.springframework.samples.petclinic.owner.Pet;
import org.springframework.samples.petclinic.owner.PetType;
import org.springframework.samples.petclinic.owner.Visit;
import org.springframework.samples.petclinic.vet.Vet;

@EnabledIfSystemProperty(named = "spring.profiles.active", matches = "dsql")
class BaseEntitySchemaTests {

  @Test
  void generatesDefaultsForIdsButNotForeignKeys() {
    StandardServiceRegistry serviceRegistry =
        new StandardServiceRegistryBuilder()
            .applySetting(
                "hibernate.dialect", "software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect")
            .applySetting("hibernate.boot.allow_jdbc_metadata_access", false)
            .build();

    try {
      Metadata metadata =
          new MetadataSources(serviceRegistry)
              .addAnnotatedClass(Owner.class)
              .addAnnotatedClass(Pet.class)
              .addAnnotatedClass(PetType.class)
              .addAnnotatedClass(Specialty.class)
              .addAnnotatedClass(Vet.class)
              .addAnnotatedClass(Visit.class)
              .buildMetadata();
      StringBuilder ddl = new StringBuilder();

      serviceRegistry
          .getService(SchemaManagementTool.class)
          .getSchemaCreator(Collections.emptyMap())
          .doCreation(
              metadata,
              executionOptions(),
              ContributableMatcher.ALL,
              sourceDescriptor(),
              targetDescriptor(ddl));

      for (String tableName : List.of("owners", "pets", "specialties", "types", "vets", "visits")) {
        assertThat(tableDefinition(ddl, tableName))
            .contains("id uuid default gen_random_uuid() not null");
      }

      assertColumnWithoutDefault(ddl, "pets", "owner_id");
      assertColumnWithoutDefault(ddl, "pets", "type_id");
      assertColumnWithoutDefault(ddl, "visits", "pet_id");
      assertColumnWithoutDefault(ddl, "vet_specialties", "specialty_id");
      assertColumnWithoutDefault(ddl, "vet_specialties", "vet_id");
    } finally {
      StandardServiceRegistryBuilder.destroy(serviceRegistry);
    }
  }

  private static ExecutionOptions executionOptions() {
    return new ExecutionOptions() {
      @Override
      public Map<String, Object> getConfigurationValues() {
        return Collections.emptyMap();
      }

      @Override
      public boolean shouldManageNamespaces() {
        return false;
      }

      @Override
      public ExceptionHandler getExceptionHandler() {
        return ExceptionHandlerHaltImpl.INSTANCE;
      }
    };
  }

  private static SourceDescriptor sourceDescriptor() {
    return new SourceDescriptor() {
      @Override
      public SourceType getSourceType() {
        return SourceType.METADATA;
      }

      @Override
      public ScriptSourceInput getScriptSourceInput() {
        return null;
      }
    };
  }

  private static TargetDescriptor targetDescriptor(StringBuilder ddl) {
    return new TargetDescriptor() {
      @Override
      public EnumSet<TargetType> getTargetTypes() {
        return EnumSet.of(TargetType.SCRIPT);
      }

      @Override
      public ScriptTargetOutput getScriptTargetOutput() {
        return new ScriptTargetOutput() {
          @Override
          public void prepare() {}

          @Override
          public void accept(String command) {
            ddl.append(command).append(";\n");
          }

          @Override
          public void release() {}
        };
      }
    };
  }

  private static String tableDefinition(StringBuilder ddl, String tableName) {
    return ddl.toString()
        .lines()
        .map(line -> line.toLowerCase(Locale.ROOT).replaceAll("\\s+", " "))
        .filter(line -> line.startsWith("create table " + tableName + " "))
        .findFirst()
        .orElseThrow(() -> new AssertionError("Missing DDL for " + tableName));
  }

  private static void assertColumnWithoutDefault(
      StringBuilder ddl, String tableName, String columnName) {
    String tableDefinition = tableDefinition(ddl, tableName);
    assertThat(tableDefinition).contains(columnName + " uuid");
    assertThat(tableDefinition).doesNotContain(columnName + " uuid default");
  }
}
