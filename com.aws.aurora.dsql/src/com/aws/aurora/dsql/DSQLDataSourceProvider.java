package com.aws.aurora.dsql;

import org.jkiss.dbeaver.DBException;
import org.jkiss.dbeaver.ext.postgresql.PostgreUtils;
import org.jkiss.dbeaver.ext.postgresql.model.PostgreDataSource;
import org.jkiss.dbeaver.ext.postgresql.model.impls.PostgreServerType;
import org.jkiss.dbeaver.model.DBPDataSource;
import org.jkiss.dbeaver.model.DBPDataSourceContainer;
import org.jkiss.dbeaver.model.DBPDataSourceURLProvider;
import org.jkiss.dbeaver.model.DatabaseURL;
import org.jkiss.dbeaver.model.access.DBAAuthModel;
import org.jkiss.dbeaver.model.connection.DBPConnectionConfiguration;
import org.jkiss.dbeaver.model.connection.DBPDriver;
import org.jkiss.dbeaver.model.connection.DBPDriverConfigurationType;
import org.jkiss.dbeaver.model.impl.jdbc.JDBCDataSourceProvider;
import org.jkiss.dbeaver.model.runtime.DBRProgressMonitor;
import org.jkiss.utils.CommonUtils;

public class DSQLDataSourceProvider extends JDBCDataSourceProvider {

    @Override
    public long getFeatures() {
        return FEATURE_CATALOGS | FEATURE_SCHEMAS;
    }

    @Override
    public DBPDataSource openDataSource(DBRProgressMonitor monitor, DBPDataSourceContainer container) throws DBException {
        return new PostgreDataSource(monitor, container);
    }

    @Override
    public String getConnectionURL(DBPDriver driver, DBPConnectionConfiguration connectionInfo) {
        DBPConnectionConfiguration configToUse = connectionInfo;
        String databaseName = connectionInfo.getDatabaseName();

        if (databaseName != null && databaseName.contains("/")) {
            configToUse = new DBPConnectionConfiguration(connectionInfo);
            configToUse.setDatabaseName(databaseName.replace("/", "%2F"));
        }

        DBAAuthModel<?> authModel = configToUse.getAuthModel();

        if (authModel instanceof DBPDataSourceURLProvider sourceURLProvider) {
            String connectionURL = sourceURLProvider.getConnectionURL(driver, configToUse);
            if (CommonUtils.isNotEmpty(connectionURL)) {
                return connectionURL;
            }
        }

        if (configToUse.getConfigurationType() == DBPDriverConfigurationType.URL) {
            return configToUse.getUrl();
        }

        PostgreServerType serverType = PostgreUtils.getServerType(driver);

        if (serverType.supportsCustomConnectionURL()) {
            return DatabaseURL.generateUrlByTemplate(driver, configToUse);
        }

        StringBuilder url = new StringBuilder("jdbc:aws-dsql:postgresql://");
        String hostName = configToUse.getHostName();
        if (!CommonUtils.isEmpty(hostName)) {
            url.append(hostName);
        } else {
            // Handle missing hostname appropriately
            throw new IllegalArgumentException("Hostname is required for DSQL connection");
        }

        if (!CommonUtils.isEmpty(configToUse.getHostPort())) {
            url.append(":").append(configToUse.getHostPort());
        }

        url.append("/");

        if (!CommonUtils.isEmpty(configToUse.getDatabaseName())) {
            url.append(configToUse.getDatabaseName());
        }
        return url.toString();
    }
}
