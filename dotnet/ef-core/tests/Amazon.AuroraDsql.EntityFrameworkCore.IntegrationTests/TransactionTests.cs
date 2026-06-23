using Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class TransactionTests : IClassFixture<DsqlTestFixture>
{
    private readonly DsqlTestFixture _fixture;

    public TransactionTests(DsqlTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task ExplicitTransaction_Commit_PersistsData()
    {
        await using var context = _fixture.CreateContext();
        var strategy = context.Database.CreateExecutionStrategy();
        var categoryId = Guid.NewGuid();

        await strategy.ExecuteInTransactionAsync(
            context,
            async (ctx, ct) =>
            {
                ctx.Categories.Add(new Category { Id = categoryId, Name = "Committed" });
                await ctx.SaveChangesAsync(ct);
            },
            async (ctx, ct) =>
            {
                ctx.ChangeTracker.Clear();
                return await ctx.Categories.AsNoTracking()
                    .AnyAsync(c => c.Id == categoryId, ct);
            });

        await using var verify = _fixture.CreateContext();
        var retrieved = await verify.Categories.FindAsync(categoryId);
        Assert.NotNull(retrieved);
        Assert.Equal("Committed", retrieved.Name);
    }

    [Fact]
    public async Task ExplicitTransaction_Rollback_DiscardsData()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        await using var transaction = await context.Database.BeginTransactionAsync();
        context.Categories.Add(new Category { Id = categoryId, Name = "Rolledback" });
        await context.SaveChangesAsync();
        await transaction.RollbackAsync();

        await using var newContext = _fixture.CreateContext();
        var retrieved = await newContext.Categories.FindAsync(categoryId);
        Assert.Null(retrieved);
    }

    [Fact]
    public async Task ExplicitTransaction_MultipleSaveChanges_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var strategy = context.Database.CreateExecutionStrategy();
        var id1 = Guid.NewGuid();
        var id2 = Guid.NewGuid();

        await strategy.ExecuteInTransactionAsync(
            context,
            async (ctx, ct) =>
            {
                ctx.Categories.Add(new Category { Id = id1, Name = "First" });
                await ctx.SaveChangesAsync(ct);
                ctx.Categories.Add(new Category { Id = id2, Name = "Second" });
                await ctx.SaveChangesAsync(ct);
            },
            async (ctx, ct) =>
            {
                ctx.ChangeTracker.Clear();
                var count = await ctx.Categories.AsNoTracking()
                    .CountAsync(c => c.Id == id1 || c.Id == id2, ct);
                return count == 2;
            });

        var count = await context.Categories
            .Where(c => c.Id == id1 || c.Id == id2)
            .CountAsync();
        Assert.Equal(2, count);
    }

    [Fact]
    public async Task ExplicitTransaction_WithIsolationLevel_SucceedsAndLogs()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        await using var transaction = await context.Database.BeginTransactionAsync(System.Data.IsolationLevel.Serializable);
        context.Categories.Add(new Category { Id = categoryId, Name = "IsolationTest" });
        await context.SaveChangesAsync();
        await transaction.CommitAsync();

        var retrieved = await context.Categories.FindAsync(categoryId);
        Assert.NotNull(retrieved);
    }

    [Fact]
    public async Task ExplicitTransaction_RollbackUpdate_RestoresOriginalValue()
    {
        var categoryId = Guid.NewGuid();

        await using (var setupContext = _fixture.CreateContext())
        {
            setupContext.Categories.Add(new Category { Id = categoryId, Name = "Original" });
            await setupContext.SaveChangesAsync();
        }

        await using (var context = _fixture.CreateContext())
        {
            await using var transaction = await context.Database.BeginTransactionAsync();
            var category = await context.Categories.FindAsync(categoryId);
            Assert.NotNull(category);
            category.Name = "Modified";
            await context.SaveChangesAsync();
            await transaction.RollbackAsync();
        }

        await using (var verifyContext = _fixture.CreateContext())
        {
            var category = await verifyContext.Categories.FindAsync(categoryId);
            Assert.NotNull(category);
            Assert.Equal("Original", category.Name);
        }
    }
}
