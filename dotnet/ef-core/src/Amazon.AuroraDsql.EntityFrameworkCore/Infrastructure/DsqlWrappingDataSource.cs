// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

/// <summary>
/// Wraps NpgsqlDataSource to return wrapped connections for DSQL compatibility.
/// </summary>
internal sealed class DsqlWrappingDataSource : DbDataSource
{
    private readonly NpgsqlDataSource _innerDataSource;
    private readonly ILoggerFactory? _loggerFactory;

    public DsqlWrappingDataSource(NpgsqlDataSource innerDataSource, ILoggerFactory? loggerFactory = null)
    {
        _innerDataSource = innerDataSource ?? throw new ArgumentNullException(nameof(innerDataSource));
        _loggerFactory = loggerFactory;
    }

    public override string ConnectionString => _innerDataSource.ConnectionString;

    protected override DbConnection CreateDbConnection()
    {
        var innerConnection = (NpgsqlConnection)_innerDataSource.CreateConnection();
        return new DsqlConnectionWrapper(innerConnection, _loggerFactory);
    }

    protected override DbConnection OpenDbConnection()
    {
        var connection = CreateDbConnection();
        try
        {
            connection.Open();
            return connection;
        }
        catch
        {
            connection.Dispose();
            throw;
        }
    }

    protected override async ValueTask<DbConnection> OpenDbConnectionAsync(CancellationToken cancellationToken = default)
    {
        var connection = CreateDbConnection();
        try
        {
            await connection.OpenAsync(cancellationToken).ConfigureAwait(false);
            return connection;
        }
        catch
        {
            await connection.DisposeAsync().ConfigureAwait(false);
            throw;
        }
    }

    // _innerDataSource is owned by DsqlDataSource — do not dispose here.
    protected override void Dispose(bool disposing)
    {
        base.Dispose(disposing);
    }

    protected override ValueTask DisposeAsyncCore()
    {
        return default;
    }
}