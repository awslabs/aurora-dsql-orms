package software.aws.aurora.dsql.dbeaver.ui.internal;

import org.eclipse.osgi.util.NLS;

public class DSQLMessages extends NLS {

    private static final String BUNDLE_NAME = "software.aws.aurora.dsql.dbeaver.ui.internal.DSQLResources";
    public static String label_dsql_endpoint;
    public static String label_username;
    public static String label_aws_profile;
    public static String label_aws_region;
    public static String place_holder_profile;
    public static String place_holder_region;

    static {
        NLS.initializeMessages(BUNDLE_NAME, DSQLMessages.class);
    }

    private DSQLMessages() {
    }
}
