# DSQL Integration using JDBC with HikariCP and Hibernate Guide

## Overview

This code example demonstrates how to use Hibernate with the Aurora DSQL JDBC Connector.
The example shows you how to connect Hibernate to an Aurora DSQL cluster using HikariCP
connection pooling and perform basic database operations by leveraging the SpringPetClinic
sample logic.

Aurora DSQL is a distributed SQL database service that provides high availability and scalability for
your PostgreSQL-compatible applications.

- `Aurora DSQL JDBC Connector` handles IAM authentication automatically for Aurora DSQL clusters.

- `HikariCP` is a popular Java connection pool that manages JDBC connections efficiently.

- `Hibernate` is the most popular Object-Relational mapping framework for Java that allows you to interact with databases using Java code.

## ⚠️ Important

- Running this code might result in charges to your AWS account.
- We recommend that you grant your code least privilege. At most, grant only the
  minimum permissions required to perform the task. For more information, see
  [Grant least privilege](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#grant-least-privilege).
- This code is not tested in every AWS Region. For more information, see
  [AWS Regional Services](https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services).

## About the code example

The example demonstrates a flexible connection approach that works for both admin and non-admin users:

- When connecting as an **admin user**, the example uses the `public` schema and generates an admin authentication
  token.
- When connecting as a **non-admin user**, the example uses a custom `myschema` schema and generates a standard
  authentication token.

The code automatically detects the user type and adjusts its behavior accordingly.

## Prerequisites

- You must have an AWS account, and have your default credentials and AWS Region
  configured as described in the
  [Globally configuring AWS SDKs and tools](https://docs.aws.amazon.com/credref/latest/refdocs/creds-config-files.html)
  guide.
- If connecting as a non-admin user, ensure the user is linked to an IAM role and is granted access to the `myschema`
  schema. See the
  [Using database roles with IAM roles](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html)
  guide.
- Verify that your version of Java is 1.8 or higher
- AWS SDK for Java
- DDL population scripts depend on `aws` cli and `psql` client to be installed.
  - <https://docs.aws.amazon.com/cli/>
  - <https://docs.aws.amazon.com/aurora-dsql/latest/userguide/getting-started.html#accessing-sql-clients-psql>
- Alternatively use <https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html>

## Run the example

### Cloud Shell DDL Setup (Optional)

1. Your IAM identity must have permission to [sign in AWS Management Console](https://docs.aws.amazon.com/signin/latest/userguide/console-sign-in-tutorials.html)
2. Sign in to the AWS Management Console and open the Aurora DSQL console at <https://console.aws.amazon.com/dsql>
3. Navigate to your cluster: [Clusters](https://us-east-1.console.aws.amazon.com/dsql/clusters/home)
4. Select your cluster (eg. h4abtt2drceddyfw4ylkrmv2nm)
5. Open CloudShell
6. Using Actions menu | Upload file | create_petclinic.sh
7. Using Actions menu | Upload file | petclinic.sql
8. Cluster Actions menu | Connect
   - Copy Endpoint (Host)
9. CloudShell Terminal

```bash
# Clone the entire repository
git clone https://github.com/awslabs/aurora-dsql-orms.git
# Change to the specific directory
cd aurora-dsql-orms/java/hibernate/examples/pet-clinic-app
 export CLUSTER_ENDPOINT=<Paste endpoint>
 export REGION=<Cluster region>
 export CLUSTER_USER=admin
 export CLUSTER_SCHEMA=postgres

  chmod +x create_petclinic.sh
  ./create_petclinic.sh
```

### Linux/Mac

Execute the following commands to set up your environment, then choose either the Gradle or Maven build options below:

```bash
# Clone the entire repository
git clone https://github.com/awslabs/aurora-dsql-orms.git
# Change to the specific directory
cd aurora-dsql-orms/java/hibernate/examples/pet-clinic-app

# create_petclinic.sh step is optional if completed in Cloud Shell
# Download the Amazon root certificate from the official trust store:
wget https://www.amazontrust.com/repository/AmazonRootCA1.pem -O root.pem
export PGSSLROOTCERT=root.pem
./create_petclinic.sh
```

#### Gradle build
```bash
./gradlew clean
./gradlew bootRun
```

#### Maven build

```bash
./mvnw clean
./mvnw spring-boot:run
```

### Windows

```bash
# Clone the entire repository
git clone https://github.com/awslabs/aurora-dsql-orms.git
# Change to the specific directory
cd aurora-dsql-orms\java\hibernate\examples\pet-clinic-app
# create_petclinic.bat step is optional if completed in Cloud Shell
curl -o root.pem https://www.amazontrust.com/repository/AmazonRootCA1.pem
set PGSSLROOTCERT=root.pem
create_petclinic.bat
gradlew.bat clean
gradlew.bat bootRun
```

# DSQL code examples

## Setting Up Connection Properties

The Aurora DSQL JDBC Connector handles IAM authentication automatically. Simply configure HikariCP with the connector's JDBC URL scheme:

```java
package org.springframework.samples.petclinic.config;

import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import org.springframework.beans.factory.annotation.Value;

import com.zaxxer.hikari.HikariDataSource;

import java.util.logging.Logger;

@Configuration(proxyBeanMethods = false)
@Profile("dsql")
public class DsqlDataSourceConfig {

  final Logger logger = Logger.getLogger(this.toString());

  @Value("${spring.datasource.username:admin}")
  private String username;

  @Bean
  @Primary
  @ConfigurationProperties("spring.datasource")
  public DataSourceProperties dataSourceProperties() {
    return new DataSourceProperties();
  }

  @Bean
  public HikariDataSource dataSource(DataSourceProperties properties) {
    final HikariDataSource hds = properties.initializeDataSourceBuilder().type(HikariDataSource.class).build();
    hds.setMaxLifetime(3300000); // 55 minutes (connector handles token refresh)
    hds.setExceptionOverrideClassName(DsqlExceptionOverride.class.getName());

    // Set the schema based on user type
    if (!username.equals("admin")) {
      hds.addDataSourceProperty("currentSchema", "myschema");
      logger.info("Set schema to myschema");
    }

    return hds;
  }
}
```

The connector generates IAM tokens automatically when connections are created. No manual token refresh is needed.

## Using UUID as Primary Key

DSQL does not support serialized primary keys or identity columns (auto-incrementing integers) that are commonly used in traditional relational databases. Instead, it is recommended to use UUID (Universally Unique Identifier) as the primary key for your entities.

Here's how to define a UUID primary key in your entity class:

```java
@Id
@Column(name = "id", updatable = false, nullable = false, columnDefinition = "UUID DEFAULT gen_random_uuid()")
private UUID id;
```

When using this approach, you don't need to manually set the ID when creating new entities. The database will automatically generate a new UUID for each inserted row.

Remember to import the necessary UUID class:

```java
import java.util.UUID;
```

## Defining Entity Classes

Hibernate can automatically create/validate database tables based on your entity class definitions. Here's a simple example of how to define an entity class:

```java
import java.io.Serializable;
import java.util.UUID;

import jakarta.persistence.Column;
import org.hibernate.annotations.Generated;

import jakarta.persistence.Id;
import jakarta.persistence.MappedSuperclass;

@MappedSuperclass
public class Person implements Serializable {

    @GeneratedValue
    @Id
    @Column(name = "id", updatable = false, nullable = false, columnDefinition = "UUID DEFAULT gen_random_uuid()")
    private UUID id;

    @Column(name = "first_name")
    @NotBlank
    private String firstName;

    // Getters and setters
}
```

## Handling SQL Exceptions

To handle specific SQL exceptions (like 0C001, 0C000, 0A000) without evicting connections, implement a custom SQLExceptionOverride:

```java

public class DsqlExceptionOverride implements SQLExceptionOverride {
    @Override
    public Override adjudicate(SQLException ex) {
        final String sqlState = ex.getSQLState();

        if ("0C000".equalsIgnoreCase(sqlState) || "0C001".equalsIgnoreCase(sqlState) || (sqlState).matches("0A\\d{3}")) {
            return SQLExceptionOverride.Override.DO_NOT_EVICT;
        }

        return Override.CONTINUE_EVICT;
    }
}
```

Then, set this class in your HikariCP configuration:

```java
@Configuration(proxyBeanMethods = false)
public class DsqlDataSourceConfig {

    @Bean
    public HikariDataSource dataSource() {
        final DataSourceProperties properties = new DataSourceProperties();
        // ... other properties

        final HikariDataSource hds = properties.initializeDataSourceBuilder().type(HikariDataSource.class).build();

        // handle the connection eviction for known exception types.
        hds.setExceptionOverrideClassName(DsqlExceptionOverride.class.getName());

        // ... other properties

        return hds;
    }
}
```

## Relationships

For `@OneToMany` and `@ManyToMany` relationships, DSQL works similarly to standard Hibernate implementations. These relationships can be used to model associations between entities in your database.

For detailed information on how to use these relationships with Hibernate, please refer to the official Hibernate documentation:

- [Hibernate ORM 6.2 User Guide - Associations](https://docs.jboss.org/hibernate/orm/6.2/userguide/html_single/Hibernate_User_Guide.html#associations)

This guide provides comprehensive information on:

- One-To-Many associations
- Many-To-Many associations
- Bidirectional associations
- Association mappings
- Collection mappings

When working with DSQL, you can follow these Hibernate guidelines for setting up your entity relationships. The main difference will be in the use of UUID for primary and foreign keys(as DSQL does not support foreign keys), as discussed in the [Using UUID as Primary Key](#using-uuid-as-primary-key) section.
