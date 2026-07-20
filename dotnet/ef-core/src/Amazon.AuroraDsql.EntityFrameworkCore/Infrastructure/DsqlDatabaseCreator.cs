// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma warning disable EF1001 // Internal EF Core API usage

using Microsoft.EntityFrameworkCore.Diagnostics;
using Npgsql.EntityFrameworkCore.PostgreSQL.Storage.Internal;

namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

/// <summary>
/// Overrides Npgsql database checks for Aurora DSQL.
///
/// DSQL databases are managed externally and always provisioned, so EF Core
/// does not need to verify existence. The base NpgsqlDatabaseCreator expects
/// an NpgsqlConnection and fails with the DSQL connection wrapper during
/// migration initialization.
/// </summary>
internal sealed class DsqlDatabaseCreator : NpgsqlDatabaseCreator
{
    public DsqlDatabaseCreator(
        RelationalDatabaseCreatorDependencies dependencies,
        INpgsqlRelationalConnection connection,
        IRawSqlCommandBuilder rawSqlCommandBuilder,
        IRelationalConnectionDiagnosticsLogger connectionLogger)
        : base(dependencies, connection, rawSqlCommandBuilder, connectionLogger)
    {
    }

    public override bool Exists() => true;

    public override Task<bool> ExistsAsync(CancellationToken cancellationToken = default)
        => Task.FromResult(true);

    public override bool HasTables() => true;

    public override Task<bool> HasTablesAsync(CancellationToken cancellationToken = default)
        => Task.FromResult(true);

    public override bool EnsureCreated()
        => throw new NotSupportedException(
            "Aurora DSQL does not support EnsureCreated(). Use Database.Migrate() instead.");

    public override Task<bool> EnsureCreatedAsync(CancellationToken cancellationToken = default)
        => throw new NotSupportedException(
            "Aurora DSQL does not support EnsureCreated(). Use Database.Migrate() instead.");

    public override bool EnsureDeleted()
        => throw new NotSupportedException(
            "Aurora DSQL does not support EnsureDeleted(). DSQL databases are managed externally.");

    public override Task<bool> EnsureDeletedAsync(CancellationToken cancellationToken = default)
        => throw new NotSupportedException(
            "Aurora DSQL does not support EnsureDeleted(). DSQL databases are managed externally.");
}