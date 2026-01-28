package org.springframework.samples.petclinic.config;

import com.zaxxer.hikari.SQLExceptionOverride;
import java.sql.SQLException;
import java.util.logging.Logger;

/**
 * By the time an instance of this interface is invoked HikariCP has already made a determination to
 * evict the Connection from the pool.
 */
public class DsqlExceptionOverride implements SQLExceptionOverride {

  final Logger logger = Logger.getLogger(this.toString());

  @java.lang.Override
  public SQLExceptionOverride.Override adjudicate(SQLException ex) {
    logger.info("tt1 Adjudicating exception: " + ex);
    logger.info("SQL State: " + ex.getSQLState());

    String sqlState = ex.getSQLState();

    if ("0C000".equalsIgnoreCase(sqlState)
        || "0C001".equalsIgnoreCase(sqlState)
        || (sqlState).matches("0A\\d{3}")) {
      logger.info("Detected retryable exception: " + sqlState);
      return SQLExceptionOverride.Override.DO_NOT_EVICT;
    }

    // For all other cases, return Override.CONTINUE_EVICT to let the system handle it
    return Override.CONTINUE_EVICT;
  }
}
