package org.springframework.samples.petclinic.config;

import com.zaxxer.hikari.HikariDataSource;
import java.util.logging.Logger;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;

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
  @Primary
  public HikariDataSource dataSource(DataSourceProperties properties) {
    final HikariDataSource hds =
        properties.initializeDataSourceBuilder().type(HikariDataSource.class).build();
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
