namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

/// <summary>
/// Wraps transaction to manually execute BEGIN/COMMIT/ROLLBACK commands.
/// Prevents Npgsql from sending isolation level clauses that DSQL doesn't support.
/// </summary>
internal sealed class DsqlTransactionWrapper : DbTransaction
{
    private readonly NpgsqlConnection _innerConnection;
    private readonly DbConnection _wrapperConnection;
    private readonly ILogger? _logger;
    private bool _completed = false;

    public DsqlTransactionWrapper(
        NpgsqlConnection innerConnection,
        DbConnection wrapperConnection,
        ILogger? logger)
    {
        _innerConnection = innerConnection ?? throw new ArgumentNullException(nameof(innerConnection));
        _wrapperConnection = wrapperConnection ?? throw new ArgumentNullException(nameof(wrapperConnection));
        _logger = logger;
    }

    protected override DbConnection? DbConnection => _wrapperConnection;

    public override IsolationLevel IsolationLevel => IsolationLevel.RepeatableRead;

    public override void Commit()
    {
        if (_completed)
            throw new InvalidOperationException("This DbTransaction has completed; it is no longer usable.");

        using (var cmd = _innerConnection.CreateCommand())
        {
            cmd.CommandText = "COMMIT";
            cmd.ExecuteNonQuery();
        }

        _completed = true;
    }

    public override async Task CommitAsync(CancellationToken cancellationToken = default)
    {
        if (_completed)
            throw new InvalidOperationException("This DbTransaction has completed; it is no longer usable.");

        await using (var cmd = _innerConnection.CreateCommand())
        {
            cmd.CommandText = "COMMIT";
            await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }

        _completed = true;
    }

    public override void Rollback()
    {
        if (_completed)
            throw new InvalidOperationException("This DbTransaction has completed; it is no longer usable.");

        try
        {
            using var cmd = _innerConnection.CreateCommand();
            cmd.CommandText = "ROLLBACK";
            cmd.ExecuteNonQuery();
        }
        finally
        {
            _completed = true;
        }
    }

    public override async Task RollbackAsync(CancellationToken cancellationToken = default)
    {
        if (_completed)
            throw new InvalidOperationException("This DbTransaction has completed; it is no longer usable.");

        try
        {
            await using var cmd = _innerConnection.CreateCommand();
            cmd.CommandText = "ROLLBACK";
            await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _completed = true;
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing && !_completed)
        {
            try
            {
                Rollback();
            }
            catch (Exception ex)
            {
                _logger?.LogWarning(
                    DsqlEventId.TransactionRollbackFailed,
                    ex,
                    "Auto-rollback of uncommitted transaction failed");
            }
        }

        base.Dispose(disposing);
    }

    public override async ValueTask DisposeAsync()
    {
        if (!_completed)
        {
            try
            {
                await RollbackAsync().ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                _logger?.LogWarning(
                    DsqlEventId.TransactionRollbackFailed,
                    ex,
                    "Auto-rollback of uncommitted transaction failed");
            }
        }

        await base.DisposeAsync().ConfigureAwait(false);
    }
}
