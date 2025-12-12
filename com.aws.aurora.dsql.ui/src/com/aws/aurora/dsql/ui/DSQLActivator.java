package com.aws.aurora.dsql.ui;

import org.eclipse.jface.resource.ImageDescriptor;
import org.eclipse.ui.plugin.AbstractUIPlugin;
import org.osgi.framework.BundleContext;

public class DSQLActivator extends AbstractUIPlugin {

    public static final String PLUGIN_ID = "com.aws.aurora.dsql.ui";

    private static DSQLActivator plugin;

    public DSQLActivator() {
    }

    @Override
    public void start(BundleContext context) throws Exception {
        super.start(context);
        plugin = this;
    }

    @Override
    public void stop(BundleContext context) throws Exception {
        plugin = null;
        super.stop(context);
    }

    public static DSQLActivator getDefault() {
        if (plugin == null) {
            throw new IllegalStateException("DSQLActivator plugin is not initialized");
        }
        return plugin;
    }

    public static ImageDescriptor getImageDescriptor(String path) {
        return imageDescriptorFromPlugin(PLUGIN_ID, path);
    }

}
