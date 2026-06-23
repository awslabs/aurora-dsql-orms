using System.Text.RegularExpressions;

namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

/// <summary>
/// Wraps NpgsqlCommand to suppress DSQL-incompatible SQL commands.
/// </summary>
internal sealed class DsqlCommandWrapper : DbCommand
{
    private readonly NpgsqlCommand _innerCommand;
    private readonly DbConnection _connection;
    private readonly ILogger? _logger;
    private DbTransaction? _transaction;

    // Regex patterns to match suppressed commands (whitespace-agnostic)
    // Matches: SET TRANSACTION ISOLATION LEVEL, SET LOCAL TRANSACTION ISOLATION LEVEL, SAVEPOINT, RELEASE SAVEPOINT, ROLLBACK TO SAVEPOINT, LOCK TABLE
    private static readonly Regex SuppressedCommandPattern = new(
        @"^\s*(" +
        @"SET\s+TRANSACTION\s+ISOLATION\s+LEVEL|" +
        @"SET\s+LOCAL\s+TRANSACTION\s+ISOLATION\s+LEVEL|" +
        @"SAVEPOINT(\s+|$)|" +
        @"RELEASE\s+SAVEPOINT(\s+|$)|" +
        @"ROLLBACK\s+TO\s+SAVEPOINT(\s+|$)|" +
        @"LOCK\s+TABLE(\s+|$)" +
        @")",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public DsqlCommandWrapper(
        NpgsqlCommand innerCommand,
        DbConnection connection,
        ILogger? logger)
    {
        _innerCommand = innerCommand ?? throw new ArgumentNullException(nameof(innerCommand));
        _connection = connection ?? throw new ArgumentNullException(nameof(connection));
        _logger = logger;
    }

    /// <summary>
    /// Determines if a SQL command should be suppressed (not sent to DSQL).
    /// Handles various whitespace characters (space, tab, newline) between keywords.
    /// </summary>
    private bool ShouldSuppress(string? commandText)
    {
        if (string.IsNullOrWhiteSpace(commandText))
            return false;

        var match = SuppressedCommandPattern.Match(commandText);
        if (match.Success)
        {
            _logger?.LogDebug(
                DsqlEventId.CommandSuppressed,
                "Suppressing DSQL-incompatible command: {CommandType}",
                match.Groups[1].Value.Trim());
            return true;
        }

        return false;
    }

    #region Execution Methods (with suppression)

    public override int ExecuteNonQuery()
    {
        if (ShouldSuppress(CommandText))
            return 0; // Pretend success

        return _innerCommand.ExecuteNonQuery();
    }

    public override async Task<int> ExecuteNonQueryAsync(CancellationToken cancellationToken)
    {
        if (ShouldSuppress(CommandText))
            return 0; // Pretend success

        return await _innerCommand.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
    }

    public override object? ExecuteScalar()
    {
        if (ShouldSuppress(CommandText))
            return null; // Pretend success

        return _innerCommand.ExecuteScalar();
    }

    public override async Task<object?> ExecuteScalarAsync(CancellationToken cancellationToken)
    {
        if (ShouldSuppress(CommandText))
            return null; // Pretend success

        return await _innerCommand.ExecuteScalarAsync(cancellationToken).ConfigureAwait(false);
    }

    protected override DbDataReader ExecuteDbDataReader(CommandBehavior behavior)
    {
        if (ShouldSuppress(CommandText))
        {
            throw new NotSupportedException(
                $"Cannot execute suppressed command as reader: {CommandText}");
        }

        return _innerCommand.ExecuteReader(behavior);
    }

    protected override async Task<DbDataReader> ExecuteDbDataReaderAsync(
        CommandBehavior behavior,
        CancellationToken cancellationToken)
    {
        if (ShouldSuppress(CommandText))
        {
            throw new NotSupportedException(
                $"Cannot execute suppressed command as reader: {CommandText}");
        }

        return await _innerCommand.ExecuteReaderAsync(behavior, cancellationToken).ConfigureAwait(false);
    }

    #endregion

    #region Property Delegations

    // CommandText originates from EF Core query pipeline, not user input.
    public override string CommandText
    {
        get => _innerCommand.CommandText;
#pragma warning disable CS8765
        set => _innerCommand.CommandText = value ?? string.Empty;
#pragma warning restore CS8765
    }

    public override int CommandTimeout
    {
        get => _innerCommand.CommandTimeout;
        set => _innerCommand.CommandTimeout = value;
    }

    public override CommandType CommandType
    {
        get => _innerCommand.CommandType;
        set => _innerCommand.CommandType = value;
    }

    protected override DbConnection? DbConnection
    {
        get => _connection;
        set
        {
            // Wrapper manages connection association
            if (value != null && value != _connection)
            {
                throw new InvalidOperationException(
                    "DbConnection cannot be changed on DsqlCommandWrapper.");
            }
        }
    }

    protected override DbTransaction? DbTransaction
    {
        get => _transaction;
        // We handle transactions manually, bypassing Npgsql's transaction model,
        // so the inner command's transaction is not updated.
        set => _transaction = value;
    }

    public override bool DesignTimeVisible
    {
        get => _innerCommand.DesignTimeVisible;
        set => _innerCommand.DesignTimeVisible = value;
    }

    public override UpdateRowSource UpdatedRowSource
    {
        get => _innerCommand.UpdatedRowSource;
        set => _innerCommand.UpdatedRowSource = value;
    }

    protected override DbParameterCollection DbParameterCollection => _innerCommand.Parameters;

    #endregion

    #region Parameter and Preparation

    protected override DbParameter CreateDbParameter()
    {
        return _innerCommand.CreateParameter();
    }

    public override void Prepare()
    {
        _innerCommand.Prepare();
    }

    public override Task PrepareAsync(CancellationToken cancellationToken = default)
    {
        return _innerCommand.PrepareAsync(cancellationToken);
    }

    public override void Cancel()
    {
        _innerCommand.Cancel();
    }

    #endregion

    #region Disposal

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _innerCommand.Dispose();
        }
        base.Dispose(disposing);
    }

    public override async ValueTask DisposeAsync()
    {
        await _innerCommand.DisposeAsync().ConfigureAwait(false);
        await base.DisposeAsync().ConfigureAwait(false);
    }

    #endregion
}
