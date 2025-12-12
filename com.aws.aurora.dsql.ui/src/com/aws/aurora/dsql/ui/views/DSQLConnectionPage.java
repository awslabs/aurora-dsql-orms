package com.aws.aurora.dsql.ui.views;

import static org.jkiss.dbeaver.ext.postgresql.PostgreUtils.getServerType;

import org.eclipse.swt.SWT;
import org.eclipse.swt.events.ModifyListener;
import org.eclipse.swt.events.SelectionAdapter;
import org.eclipse.swt.events.SelectionEvent;
import org.eclipse.swt.graphics.Image;
import org.eclipse.jface.dialogs.IDialogPage;
import org.eclipse.swt.layout.GridData;
import org.eclipse.swt.layout.GridLayout;
import org.eclipse.swt.widgets.Composite;
import org.eclipse.swt.widgets.Group;
import org.eclipse.swt.widgets.Label;
import org.eclipse.swt.widgets.Text;
import org.jkiss.dbeaver.ext.postgresql.PostgreConstants;
import org.jkiss.dbeaver.ext.postgresql.model.impls.PostgreServerType;
import org.jkiss.dbeaver.model.DBPDataSourceContainer;
import org.jkiss.dbeaver.model.connection.DBPConnectionConfiguration;
import org.jkiss.dbeaver.model.connection.DBPDriver;
import org.jkiss.dbeaver.model.connection.DBPDriverConfigurationType;
import org.jkiss.dbeaver.ui.DBeaverIcons;
import org.jkiss.dbeaver.ui.IDialogPageProvider;
import org.jkiss.dbeaver.ui.UIUtils;
import org.jkiss.dbeaver.ui.dialogs.connection.ConnectionPageWithAuth;
import org.jkiss.dbeaver.ui.dialogs.connection.DriverPropertiesDialogPage;
import org.jkiss.dbeaver.ui.internal.UIConnectionMessages;
import org.jkiss.utils.CommonUtils;
import org.eclipse.ui.plugin.AbstractUIPlugin;
import org.eclipse.jface.resource.ImageDescriptor;

import com.aws.aurora.dsql.ui.internal.DSQLMessages;

public class DSQLConnectionPage extends ConnectionPageWithAuth implements IDialogPageProvider {

    private static final String CONN_PROPERTY_PROFILE = "profile";
    private static final String CONN_PROPERTY_REGION = "region";

    private static final String DEFAULT_PORT = "5432";
    private static final String DEFAULT_DATABASE = "postgres";
    private static final String DEFAULT_PROFILE = "default";
    private static final String DEFAULT_ENDPOINT_TEMPLATE = "{clusterid}.dsql.{region}.on.aws";

    private Text urlText;
    private Text hostText;
    private String port;
    private String db;
    private boolean activated = false;
    private Image dsqlImage;

    private Text userNameText;
    private Text profileText;
    private Text regionText;

    @Override
    public void dispose() {
        if (dsqlImage != null && !dsqlImage.isDisposed()) {
            dsqlImage.dispose();
            dsqlImage = null;
        }
        super.dispose();
    }

    @Override
    protected void createAuthPanel(Composite parent, int gridColumns) {

        // Create a hidden composite for parent's auth panel
        Composite hiddenComposite = new Composite(parent, SWT.NONE);
        GridData hiddenGd = new GridData();
        hiddenGd.exclude = true;
        hiddenComposite.setLayoutData(hiddenGd);
        hiddenComposite.setVisible(false);

        // Bug fix for 24.3.5 Dbeaver authModelSelector is null
        // Initialize auth model selector in a hidden composite
        super.createAuthPanel(hiddenComposite, gridColumns);

        Group myGroup = UIUtils.createControlGroup(
                parent,
                "Authentication",
                2, // number of columns
                GridData.FILL_HORIZONTAL,
                0
        );

        Label userNameLabel = UIUtils.createControlLabel(myGroup, DSQLMessages.label_username);
        userNameText = new Text(myGroup, SWT.BORDER);
        GridData userNameGD = new GridData(GridData.HORIZONTAL_ALIGN_BEGINNING);
        userNameGD.widthHint = 200;
        userNameText.setLayoutData(userNameGD);
        userNameText.addModifyListener(e -> site.updateButtons());

        Label profileLabel = UIUtils.createControlLabel(myGroup, DSQLMessages.label_aws_profile);
        profileText = new Text(myGroup, SWT.BORDER);
        profileText.setMessage(DSQLMessages.place_holder_profile);
        GridData profileGD = new GridData(GridData.HORIZONTAL_ALIGN_BEGINNING);
        profileGD.widthHint = 200;
        profileText.setLayoutData(profileGD);
        profileText.addModifyListener(e -> site.updateButtons());

        Label regionLabel = UIUtils.createControlLabel(myGroup, DSQLMessages.label_aws_region);
        regionText = new Text(myGroup, SWT.BORDER);
        regionText.setMessage(DSQLMessages.place_holder_region);
        GridData regionGD = new GridData(GridData.HORIZONTAL_ALIGN_BEGINNING);
        regionGD.widthHint = 200;
        regionText.setLayoutData(regionGD);
        regionText.addModifyListener(e -> site.updateButtons());

    }

    @Override
    public Image getImage() {
        if (dsqlImage == null) {
            ImageDescriptor descriptor = AbstractUIPlugin.imageDescriptorFromPlugin(
                    "com.aws.aurora.dsql",
                    "icons/dsql_logo.png"
            );
            if (descriptor != null) {
                dsqlImage = descriptor.createImage();
            }
        }
        return dsqlImage;
    }

    @Override
    public void createControl(Composite composite) {
        final ModifyListener textListener = e -> {
            if (activated) {
                updateUrl();
                site.updateButtons();
            }
        };

        Composite mainGroup = new Composite(composite, SWT.NONE);
        mainGroup.setLayout(new GridLayout(1, false));
        GridData gd = new GridData(GridData.FILL_BOTH);
        mainGroup.setLayoutData(gd);

        Group addrGroup = UIUtils.createControlGroup(
                mainGroup,
                UIConnectionMessages.dialog_connection_server_label,
                4,
                GridData.FILL_HORIZONTAL,
                0
        );

        SelectionAdapter typeSwitcher = new SelectionAdapter() {
            @Override
            public void widgetSelected(SelectionEvent e) {
                setupConnectionModeSelection(urlText, typeURLRadio.getSelection(), GROUP_CONNECTION_ARR);

                boolean urlMode = typeURLRadio.getSelection();
                if (userNameText != null) {
                    userNameText.setEnabled(!urlMode);
                }
                if (profileText != null) {
                    profileText.setEnabled(!urlMode);
                }
                if (regionText != null) {
                    regionText.setEnabled(!urlMode);
                }

                updateUrl();
            }
        };
        createConnectionModeSwitcher(addrGroup, typeSwitcher);

        UIUtils.createControlLabel(addrGroup, UIConnectionMessages.dialog_connection_url_label);
        urlText = new Text(addrGroup, SWT.BORDER);
        gd = new GridData(GridData.FILL_HORIZONTAL);
        gd.horizontalSpan = 3;
        gd.grabExcessHorizontalSpace = true;
        gd.widthHint = 355;
        urlText.setLayoutData(gd);
        urlText.addModifyListener(e -> site.updateButtons());

        Label hostLabel = UIUtils.createControlLabel(
                addrGroup,
                DSQLMessages.label_dsql_endpoint
        );
        hostText = new Text(addrGroup, SWT.BORDER);
        gd = new GridData(GridData.FILL_HORIZONTAL);
        gd.grabExcessHorizontalSpace = true;
        hostText.setLayoutData(gd);
        hostText.addModifyListener(textListener);
        addControlToGroup(GROUP_CONNECTION, hostLabel, hostText);
        gd.horizontalSpan = 3;

        createAuthPanel(mainGroup, 1);

        createDriverPanel(mainGroup);
        setControl(mainGroup);
    }

    @Override
    public boolean isComplete() {
        if (isCustomURL()) {
            return !CommonUtils.isEmpty(urlText.getText());
        } else {
            return !CommonUtils.isEmpty(hostText.getText())
                    && !CommonUtils.isEmpty(userNameText.getText());
        }
    }

    @Override
    public void loadSettings() {

        DBPDataSourceContainer activeDataSource = site.getActiveDataSource();

        if (activeDataSource == null) {
            return;
        }

        DBPConnectionConfiguration connectionInfo = activeDataSource.getConnectionConfiguration();
        final DBPDriver driver = site.getDriver();

        super.loadSettings();

        // Load values from new connection info
        if (hostText != null) {
            if (!CommonUtils.isEmpty(connectionInfo.getHostName())) {
                hostText.setText(connectionInfo.getHostName());
            } else {
                hostText.setText(DEFAULT_ENDPOINT_TEMPLATE);
            }
        }

        // Load values into a String. These fields are not required for DSQL.
        // Default port is 5432, Default databaseName is postgres.
        if (!CommonUtils.isEmpty(connectionInfo.getHostPort())) {
            port = connectionInfo.getHostPort();
        } else if (getSite().isNew()) {
            port = CommonUtils.notEmpty(driver.getDefaultPort());
        } else {
            port = DEFAULT_PORT;
        }

        String databaseName = connectionInfo.getDatabaseName();
        if (CommonUtils.isEmpty(databaseName)) {
            if (getSite().isNew()) {
                databaseName = driver.getDefaultDatabase();
                if (CommonUtils.isEmpty(databaseName)) {
                    databaseName = PostgreConstants.DEFAULT_DATABASE;
                }
            } else {
                databaseName = DEFAULT_DATABASE;
            }
        }
        db = databaseName;

        final boolean useURL = connectionInfo.getConfigurationType() == DBPDriverConfigurationType.URL;
        if (useURL) {
            urlText.setText(connectionInfo.getUrl());
        }
        setupConnectionModeSelection(urlText, useURL, GROUP_CONNECTION_ARR);
        updateUrl();

        if (userNameText != null) {
            String username = connectionInfo.getUserName();
            if (!CommonUtils.isEmpty(username)) {
                userNameText.setText(username);
            }
        }

        if (profileText != null) {
            String profile = connectionInfo.getProperty(CONN_PROPERTY_PROFILE);
            if (profile != null && !profile.isEmpty()) {
                profileText.setText(CommonUtils.notEmpty(profile));
            } else {
                profileText.setText(DEFAULT_PROFILE);
            }

        }

        if (regionText != null) {
            String region = connectionInfo.getProperty(CONN_PROPERTY_REGION);
            regionText.setText(CommonUtils.notEmpty(region));
        }

        activated = true;
    }

    @Override
    public void saveSettings(DBPDataSourceContainer dataSource) {
        DBPConnectionConfiguration connectionInfo = dataSource.getConnectionConfiguration();
        if (typeURLRadio != null) {
            connectionInfo.setConfigurationType(
                    typeURLRadio.getSelection() ? DBPDriverConfigurationType.URL : DBPDriverConfigurationType.MANUAL);
        }

        if (hostText != null) {
            connectionInfo.setHostName(hostText.getText().trim());
        }

        if (port != null) {
            connectionInfo.setHostPort(port);
        }

        if (db != null) {
            connectionInfo.setDatabaseName(db);
        }

        if (typeURLRadio != null && typeURLRadio.getSelection()) {
            if (urlText != null) {
                connectionInfo.setUrl(urlText.getText());
            }
        }

        if (profileText != null) {
            connectionInfo.setProperty(CONN_PROPERTY_PROFILE, profileText.getText().trim());
        }

        // avoid saving empty as the region as the JDBC connector will try to use empty as the region
        if (regionText != null && !CommonUtils.isEmpty(regionText.getText().trim())) {
            connectionInfo.setProperty(CONN_PROPERTY_REGION, regionText.getText().trim());
        }

        // this is intentionally placed before saving the user name as the parent method keep saving the default user "admin" 
        super.saveSettings(dataSource);

        if (userNameText != null) {
            connectionInfo.setUserName(userNameText.getText().trim());
        }
    }

    @Override
    public IDialogPage[] getDialogPages(boolean extrasOnly, boolean forceCreate) {
        return new IDialogPage[]{
            new DriverPropertiesDialogPage(this)
        };
    }

    private void updateUrl() {
        DBPDataSourceContainer dataSourceContainer = site.getActiveDataSource();
        if (dataSourceContainer == null) {
            return;
        }

        DBPConnectionConfiguration config = dataSourceContainer.getConnectionConfiguration();
        if (config == null) {
            return;
        }

        if (typeURLRadio != null && typeURLRadio.getSelection()) {

            urlText.setText(config.getUrl());
        } else {
            DBPDriver driver = dataSourceContainer.getDriver();
            if (driver == null) {
                return;
            }
            urlText.setText(driver.getConnectionURL(config));
        }
    }
}
