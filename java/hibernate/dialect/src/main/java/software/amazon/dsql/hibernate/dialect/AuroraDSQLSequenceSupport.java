// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect;

import org.hibernate.dialect.sequence.SequenceSupport;

public class AuroraDSQLSequenceSupport implements SequenceSupport {

    private final int sequenceCacheSize;

    public AuroraDSQLSequenceSupport(int sequenceCacheSize) {
        this.sequenceCacheSize = sequenceCacheSize;
    }

    @Override
    public String getCreateSequenceString(String sequenceName) {
        return "create sequence " + sequenceName + " cache " + sequenceCacheSize;
    }

    @Override
    public String getSelectSequenceNextValString(String sequenceName) {
        return "nextval('" + sequenceName + "')";
    }

    @Override
    public boolean sometimesNeedsStartingValue() {
        return true;
    }

    @Override
    public String getDropSequenceString(String sequenceName) {
        return "drop sequence if exists " + sequenceName;
    }
}
