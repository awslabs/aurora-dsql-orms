// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

/// <summary>
/// Event IDs for DSQL adapter diagnostics.
/// Range: 100001-100099 reserved for DSQL adapter events.
/// </summary>
internal static class DsqlEventId
{
    /// <summary>
    /// Event ID for logging suppressed commands.
    /// </summary>
    public static readonly EventId CommandSuppressed = new(100001, nameof(CommandSuppressed));

    /// <summary>
    /// Event ID for logging ignored isolation level warnings.
    /// </summary>
    public static readonly EventId IsolationLevelIgnored = new(100002, nameof(IsolationLevelIgnored));

    /// <summary>
    /// Event ID for logging transaction rollback failures.
    /// </summary>
    public static readonly EventId TransactionRollbackFailed = new(100003, nameof(TransactionRollbackFailed));

    /// <summary>
    /// Event ID for logging OCC retry attempts.
    /// </summary>
    public static readonly EventId OccRetry = new(100004, nameof(OccRetry));

    /// <summary>
    /// Event ID for behavior-changing dsql-lint rewrites during migration (e.g. FK removal).
    /// </summary>
    public static readonly EventId MigrationTransformWarning = new(100005, nameof(MigrationTransformWarning));
}