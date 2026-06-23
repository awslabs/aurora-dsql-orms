using Microsoft.EntityFrameworkCore.Infrastructure;

namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

/// <summary>
/// Execution strategy that retries operations failing with OCC conflicts.
/// Delegates error detection to <see cref="OccRetry.IsOccError"/> (SqlState 40001, OC000, OC001).
/// Uses exponential backoff with jitter.
/// </summary>
public class DsqlExecutionStrategy : ExecutionStrategy
{
    /// <summary>Default maximum retry attempts for OCC conflicts.</summary>
    public new const int DefaultMaxRetryCount = 6;

    /// <summary>Default maximum delay between retries.</summary>
    public static readonly TimeSpan DefaultMaxRetryDelay = TimeSpan.FromSeconds(30);

    private readonly ILogger? _logger;

    /// <summary>
    /// Creates a new instance with default retry settings (6 retries, 30s max delay).
    /// </summary>
    public DsqlExecutionStrategy(ExecutionStrategyDependencies dependencies)
        : base(dependencies, DefaultMaxRetryCount, DefaultMaxRetryDelay)
    {
        _logger = ResolveLogger(dependencies);
    }

    /// <summary>
    /// Creates a new instance with configurable retry parameters.
    /// </summary>
    public DsqlExecutionStrategy(
        ExecutionStrategyDependencies dependencies,
        int maxRetryCount,
        TimeSpan maxRetryDelay)
        : base(dependencies, maxRetryCount, maxRetryDelay)
    {
        _logger = ResolveLogger(dependencies);
    }

    private static ILogger? ResolveLogger(ExecutionStrategyDependencies dependencies)
    {
        return dependencies.CurrentContext.Context
            .GetInfrastructure()
            .GetService<ILoggerFactory>()
            ?.CreateLogger("Amazon.AuroraDsql.EntityFrameworkCore.ExecutionStrategy");
    }

    /// <inheritdoc />
    protected override void OnFirstExecution()
    {
        // Allow SaveChangesAsync inside user-initiated transactions without throwing.
        // The strategy won't retry (ShouldRetryOn returns false when inside a transaction),
        // but it won't block either. Customers use ExecuteInTransactionAsync for retry.
    }

    /// <inheritdoc />
    protected override bool ShouldRetryOn(Exception exception)
    {
        if (Dependencies.CurrentContext.Context.Database.CurrentTransaction is not null)
            return false;

        var current = exception;
        while (current is not null)
        {
            if (OccRetry.IsOccError(current))
            {
                _logger?.LogDebug(
                    DsqlEventId.OccRetry,
                    "Retrying operation due to OCC conflict (SqlState 40001). Attempt {Attempt}.",
                    ExceptionsEncountered.Count);
                return true;
            }
            current = current.InnerException;
        }

        return false;
    }

    /// <inheritdoc />
    protected override TimeSpan? GetNextDelay(Exception lastException)
    {
        var baseDelay = base.GetNextDelay(lastException);
        if (baseDelay == null)
            return null;

        var jitterMs = Random.Shared.NextDouble() * 0.2 * baseDelay.Value.TotalMilliseconds;
        return baseDelay.Value + TimeSpan.FromMilliseconds(jitterMs);
    }
}
