namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

/// <summary>
/// Wraps NpgsqlConnection to intercept command and transaction creation.
/// </summary>
internal sealed class DsqlConnectionWrapper : DbConnection
{
    private readonly NpgsqlConnection _innerConnection;
    private readonly ILogger? _commandLogger;
    private readonly ILogger? _transactionLogger;

    public DsqlConnectionWrapper(
        NpgsqlConnection innerConnection,
        ILoggerFactory? loggerFactory)
    {
        _innerConnection = innerConnection ?? throw new ArgumentNullException(nameof(innerConnection));
        _commandLogger = loggerFactory?.CreateLogger("Amazon.AuroraDsql.EntityFrameworkCore.Command");
        _transactionLogger = loggerFactory?.CreateLogger("Amazon.AuroraDsql.EntityFrameworkCore.Transaction");
    }

    public override string ConnectionString
    {
        get => _innerConnection.ConnectionString;
#pragma warning disable CS8765
        set => _innerConnection.ConnectionString = value ?? string.Empty;
#pragma warning restore CS8765
    }

    public override string Database => _innerConnection.Database;

    public override string DataSource => _innerConnection.DataSource;

    public override string ServerVersion => _innerConnection.ServerVersion;

    public override ConnectionState State => _innerConnection.State;

    public override void ChangeDatabase(string databaseName)
    {
        _innerConnection.ChangeDatabase(databaseName);
    }

    public override void Open()
    {
        _innerConnection.Open();
    }

    public override async Task OpenAsync(CancellationToken cancellationToken)
    {
        await _innerConnection.OpenAsync(cancellationToken).ConfigureAwait(false);
    }

    public override void Close()
    {
        _innerConnection.Close();
    }

    public override async Task CloseAsync()
    {
        await _innerConnection.CloseAsync().ConfigureAwait(false);
    }

    protected override DbCommand CreateDbCommand()
    {
        var innerCommand = _innerConnection.CreateCommand();
        return new DsqlCommandWrapper(innerCommand, this, _commandLogger);
    }

    protected override DbTransaction BeginDbTransaction(IsolationLevel isolationLevel)
    {
        if (isolationLevel != IsolationLevel.Unspecified && isolationLevel != IsolationLevel.RepeatableRead)
        {
            _transactionLogger?.LogWarning(
                DsqlEventId.IsolationLevelIgnored,
                "DSQL uses fixed OCC isolation. Requested isolation level {IsolationLevel} is ignored.",
                isolationLevel);
        }

        // Manually send BEGIN without isolation level
        using (var cmd = _innerConnection.CreateCommand())
        {
            cmd.CommandText = "BEGIN";
            cmd.ExecuteNonQuery();
        }

        return new DsqlTransactionWrapper(_innerConnection, this, _transactionLogger);
    }

    protected override async ValueTask<DbTransaction> BeginDbTransactionAsync(
        IsolationLevel isolationLevel,
        CancellationToken cancellationToken)
    {
        if (isolationLevel != IsolationLevel.Unspecified && isolationLevel != IsolationLevel.RepeatableRead)
        {
            _transactionLogger?.LogWarning(
                DsqlEventId.IsolationLevelIgnored,
                "DSQL uses fixed OCC isolation. Requested isolation level {IsolationLevel} is ignored.",
                isolationLevel);
        }

        // Manually send BEGIN without isolation level
        await using (var cmd = _innerConnection.CreateCommand())
        {
            cmd.CommandText = "BEGIN";
            await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }

        return new DsqlTransactionWrapper(_innerConnection, this, _transactionLogger);
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _innerConnection.Dispose();
        }
        base.Dispose(disposing);
    }

    public override async ValueTask DisposeAsync()
    {
        await _innerConnection.DisposeAsync().ConfigureAwait(false);
        await base.DisposeAsync().ConfigureAwait(false);
    }
}
