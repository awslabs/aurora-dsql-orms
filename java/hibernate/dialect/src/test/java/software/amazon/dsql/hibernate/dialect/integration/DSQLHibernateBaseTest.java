// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect.integration;

import static org.hibernate.cfg.AvailableSettings.DIALECT;
import static org.hibernate.cfg.AvailableSettings.PASS;
import static org.hibernate.cfg.AvailableSettings.SHOW_SQL;
import static org.hibernate.cfg.AvailableSettings.URL;
import static org.hibernate.cfg.AvailableSettings.USER;

import java.util.ArrayList;
import java.util.List;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.cfg.Configuration;
import org.hibernate.cfg.Environment;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.dsql.DsqlUtilities;
import software.amazon.awssdk.services.dsql.model.GenerateAuthTokenRequest;

public abstract class DSQLHibernateBaseTest {

  public static final String username = "admin";
  public static final String endpoint = System.getenv("CLUSTER_ENDPOINT");
  public static final Region region = Region.of(System.getenv("REGION"));
  public static final String url =
      "jdbc:postgresql://" + endpoint + "/postgres?sslMode=verify-full&sslNegotiation=direct";

  protected Configuration configuration;
  protected SessionFactory sessionFactory;

  protected static String generateToken() {
    DsqlUtilities dsqlUtilities =
        DsqlUtilities.builder()
            .region(region)
            .credentialsProvider(DefaultCredentialsProvider.create())
            .build();

    GenerateAuthTokenRequest tokenGenerator =
        GenerateAuthTokenRequest.builder().hostname(endpoint).region(region).build();
    return dsqlUtilities.generateDbConnectAdminAuthToken(tokenGenerator);
  }

  protected Session getSession() {
    return sessionFactory.openSession();
  }

  private static Configuration createConfiguration() {
    Configuration configuration =
        new Configuration()
            .setProperty(URL, url)
            .setProperty(USER, username)
            .setProperty(PASS, generateToken())
            .setProperty(SHOW_SQL, "true")
            .setProperty(DIALECT, "software.amazon.dsql.hibernate.dialect.AuroraDSQLDialect");
    configuration.setProperty(Environment.HBM2DDL_AUTO, "create");
    return configuration;
  }

  protected List<Class<?>> getAnnotatedClasses() {
    return new ArrayList<>();
  }

  @BeforeEach
  public void beforeEach() {
    this.configuration = createConfiguration();
    getAnnotatedClasses().forEach(configuration::addAnnotatedClass);
    this.sessionFactory = configuration.buildSessionFactory();
  }

  @AfterEach
  public void afterEach() {
    sessionFactory.close();
  }
}
