// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.EnumSet;
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
import software.amazon.dsql.hibernate.dialect.integration.model.M2OEntityA;
import software.amazon.dsql.hibernate.dialect.integration.model.M2OEntityB;

class AuroraDSQLForeignKeyExporterTest {

  @Test
  void generatesAndDropsForeignKeysWithSupportedDsqlSyntax() throws IOException {
    Path createScriptPath = Files.createTempFile("aurora-dsql-hibernate-fk-create-", ".sql");
    Path dropScriptPath = Files.createTempFile("aurora-dsql-hibernate-fk-drop-", ".sql");
    StandardServiceRegistry registry =
        new StandardServiceRegistryBuilder()
            .applySetting("hibernate.dialect", AuroraDSQLDialect.class.getName())
            .build();
    try {
      Metadata metadata =
          new MetadataSources(registry)
              .addAnnotatedClass(M2OEntityA.class)
              .addAnnotatedClass(M2OEntityB.class)
              .buildMetadata();
      SchemaManagementTool tool = registry.getService(SchemaManagementTool.class);

      tool.getSchemaCreator(Collections.emptyMap())
          .doCreation(
              metadata,
              executionOptions(),
              ContributableMatcher.ALL,
              sourceDescriptor(),
              targetDescriptor(createScriptPath));

      String createScript = Files.readString(createScriptPath).toLowerCase();
      assertTrue(createScript.contains("foreign key"));
      assertTrue(createScript.contains("not valid"));
      assertFalse(createScript.contains("alter table async"));

      tool.getSchemaDropper(Collections.emptyMap())
          .doDrop(
              metadata,
              executionOptions(),
              ContributableMatcher.ALL,
              sourceDescriptor(),
              targetDescriptor(dropScriptPath));

      String dropScript = Files.readString(dropScriptPath).toLowerCase();
      assertTrue(dropScript.contains("drop constraint"));
    } finally {
      StandardServiceRegistryBuilder.destroy(registry);
      Files.deleteIfExists(createScriptPath);
      Files.deleteIfExists(dropScriptPath);
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

  private static TargetDescriptor targetDescriptor(Path scriptPath) {
    return new TargetDescriptor() {
      @Override
      public EnumSet<TargetType> getTargetTypes() {
        return EnumSet.of(TargetType.SCRIPT);
      }

      @Override
      public ScriptTargetOutput getScriptTargetOutput() {
        return new ScriptTargetOutput() {
          private java.io.FileWriter writer;

          @Override
          public void prepare() {
            try {
              writer = new java.io.FileWriter(scriptPath.toFile());
            } catch (IOException e) {
              throw new RuntimeException(e);
            }
          }

          @Override
          public void accept(String command) {
            try {
              writer.write(command + ";\n");
            } catch (IOException e) {
              throw new RuntimeException(e);
            }
          }

          @Override
          public void release() {
            try {
              writer.close();
            } catch (IOException e) {
              throw new RuntimeException(e);
            }
          }
        };
      }
    };
  }
}
