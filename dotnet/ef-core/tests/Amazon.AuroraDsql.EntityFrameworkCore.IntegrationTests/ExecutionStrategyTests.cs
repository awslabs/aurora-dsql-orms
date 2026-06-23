using Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class ExecutionStrategyTests : IClassFixture<DsqlTestFixture>
{
    private readonly DsqlTestFixture _fixture;

    public ExecutionStrategyTests(DsqlTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task UseDsql_RegistersDsqlExecutionStrategy_WithCustomConfig()
    {
        await using var context = _fixture.CreateContext(dsql =>
        {
            dsql.SetMaxRetryCount(3);
            dsql.SetMaxRetryDelay(TimeSpan.FromSeconds(10));
        });

        var strategy = Assert.IsType<DsqlExecutionStrategy>(context.Database.CreateExecutionStrategy());
        Assert.Equal(3, strategy.MaxRetryCount);
        Assert.Equal(TimeSpan.FromSeconds(10), strategy.MaxRetryDelay);
    }

    // Probabilistic: 10 concurrent writers make OCC conflicts near-certain, and unretried
    // exceptions would fail Task.WhenAll — but does not assert retry count directly.
    [Fact]
    public async Task ImplicitTransaction_OccConflict_RetriesAutomatically()
    {
        var categoryId = Guid.NewGuid();

        await using (var setup = _fixture.CreateContext())
        {
            setup.Categories.Add(new Category { Id = categoryId, Name = "Original" });
            await setup.SaveChangesAsync();
        }

        // Launch concurrent writers — SaveChangesAsync retries transparently
        // without any strategy.ExecuteAsync wrapper
        const int writerCount = 10;
        var tasks = Enumerable.Range(0, writerCount).Select(async i =>
        {
            await using var ctx = _fixture.CreateContext();
            var cat = await ctx.Categories.FindAsync(categoryId);
            cat!.Name = $"Writer{i}";
            await ctx.SaveChangesAsync();
        });

        await Task.WhenAll(tasks);

        await using var verify = _fixture.CreateContext();
        var result = await verify.Categories.FindAsync(categoryId);
        Assert.StartsWith("Writer", result!.Name);
    }

    [Fact]
    public async Task ExplicitTransaction_WithoutExecuteInTransaction_DoesNotRetry()
    {
        var categoryId = Guid.NewGuid();

        await using (var setup = _fixture.CreateContext())
        {
            setup.Categories.Add(new Category { Id = categoryId, Name = "Original" });
            await setup.SaveChangesAsync();
        }

        await using var context = _fixture.CreateContext();
        await using var transaction = await context.Database.BeginTransactionAsync();

        var cat = await context.Categories.FindAsync(categoryId);

        await using var conflicting = _fixture.CreateContext();
        var c = await conflicting.Categories.FindAsync(categoryId);
        c!.Name = "Conflict";
        await conflicting.SaveChangesAsync();

        cat!.Name = "WillFail";
        await context.SaveChangesAsync();

        var ex = await Assert.ThrowsAsync<global::Npgsql.PostgresException>(
            () => transaction.CommitAsync());
        Assert.Equal("40001", ex.SqlState);
    }

    [Fact]
    public async Task UseDsql_RegistersDsqlExecutionStrategy_WithDefaults()
    {
        await using var context = _fixture.CreateContext();

        var strategy = Assert.IsType<DsqlExecutionStrategy>(context.Database.CreateExecutionStrategy());
        Assert.Equal(6, strategy.MaxRetryCount);
        Assert.Equal(TimeSpan.FromSeconds(30), strategy.MaxRetryDelay);
    }

    [Fact]
    public async Task ExplicitTransaction_ThrowsRetryLimitExceeded_WhenRetriesExhausted()
    {
        var categoryId = Guid.NewGuid();

        await using (var setup = _fixture.CreateContext())
        {
            setup.Categories.Add(new Category { Id = categoryId, Name = "Original" });
            await setup.SaveChangesAsync();
        }

        await using var context = _fixture.CreateContext(dsql => dsql.SetMaxRetryCount(1));
        var strategy = context.Database.CreateExecutionStrategy();
        var attemptCount = 0;

        var ex = await Assert.ThrowsAsync<RetryLimitExceededException>(() =>
            strategy.ExecuteInTransactionAsync(
                context,
                async (ctx, ct) =>
                {
                    attemptCount++;
                    ctx.ChangeTracker.Clear();
                    var cat = await ctx.Categories.FindAsync(new object[] { categoryId }, ct);

                    // Conflicting write on every attempt — OCC always fires
                    await using var conflicting = _fixture.CreateContext();
                    var c = await conflicting.Categories.FindAsync(categoryId);
                    c!.Name = $"Conflict{attemptCount}";
                    await conflicting.SaveChangesAsync();

                    cat!.Name = "WillFail";
                    await ctx.SaveChangesAsync(ct);
                },
                async (ctx, ct) =>
                {
                    ctx.ChangeTracker.Clear();
                    var cat = await ctx.Categories
                        .AsNoTracking()
                        .FirstOrDefaultAsync(c => c.Id == categoryId, ct);
                    return cat?.Name == "WillFail";
                }));

        Assert.Equal(2, attemptCount); // 1 initial + 1 retry
        Assert.IsType<global::Npgsql.PostgresException>(ex.InnerException);
    }

    [Fact]
    public async Task ExplicitTransaction_ExecuteInTransactionAsync_RetriesOnOcc()
    {
        var categoryId = Guid.NewGuid();

        await using (var setup = _fixture.CreateContext())
        {
            setup.Categories.Add(new Category { Id = categoryId, Name = "Original" });
            await setup.SaveChangesAsync();
        }

        // ExecuteInTransactionAsync calls BeginTransaction, runs the operation,
        // then commits. On OCC (40001), it retries the entire operation.
        // We use concurrent writers to provoke a real conflict.
        await using var context = _fixture.CreateContext();
        var strategy = context.Database.CreateExecutionStrategy();
        var attemptCount = 0;

        var barrier = new TaskCompletionSource();
        var conflictTask = Task.Run(async () =>
        {
            await barrier.Task;
            await using var conflicting = _fixture.CreateContext();
            var c = await conflicting.Categories.FindAsync(categoryId);
            c!.Name = "Conflicting";
            await conflicting.SaveChangesAsync();
        });

        await strategy.ExecuteInTransactionAsync(
            context,
            async (ctx, ct) =>
            {
                attemptCount++;
                ctx.ChangeTracker.Clear();
                var cat = await ctx.Categories.FindAsync(new object[] { categoryId }, ct);

                // On first attempt: signal the conflicting writer and wait for it to commit.
                // This creates an OCC conflict — our read snapshot is now stale.
                if (attemptCount == 1)
                {
                    barrier.TrySetResult();
                    await conflictTask;
                }

                cat!.Name = "Final";
                await ctx.SaveChangesAsync(ct);
            },
            async (ctx, ct) =>
            {
                ctx.ChangeTracker.Clear();
                var cat = await ctx.Categories
                    .AsNoTracking()
                    .FirstOrDefaultAsync(c => c.Id == categoryId, ct);
                return cat?.Name == "Final";
            });

        Assert.True(attemptCount >= 2, $"Expected retry, got {attemptCount} attempt(s)");

        await using var verify = _fixture.CreateContext();
        var result = await verify.Categories.FindAsync(categoryId);
        Assert.Equal("Final", result!.Name);
    }
}
