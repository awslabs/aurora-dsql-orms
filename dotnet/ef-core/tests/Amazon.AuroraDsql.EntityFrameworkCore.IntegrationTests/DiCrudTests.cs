namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

/// <summary>
/// CRUD tests using DI pattern (AddDsqlDataSource + UseDsql).
/// Mirrors CrudTests but verifies the recommended DI pattern works.
/// </summary>
[Collection(nameof(DsqlDiTestCollection))]
public class DiCrudTests : IClassFixture<DsqlDiTestFixture>
{
    private readonly DsqlDiTestFixture _fixture;

    public DiCrudTests(DsqlDiTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task Insert_SingleEntity_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "DI Electronics" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        var retrieved = await context.Categories.FindAsync(categoryId);
        Assert.NotNull(retrieved);
        Assert.Equal("DI Electronics", retrieved.Name);
    }

    [Fact]
    public async Task Update_SingleEntity_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "DI Books" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        category.Name = "DI Audiobooks";
        await context.SaveChangesAsync();

        var retrieved = await context.Categories.FindAsync(categoryId);
        Assert.Equal("DI Audiobooks", retrieved!.Name);
    }

    [Fact]
    public async Task Delete_SingleEntity_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "DI Obsolete" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        context.Categories.Remove(category);
        await context.SaveChangesAsync();

        var retrieved = await context.Categories.FindAsync(categoryId);
        Assert.Null(retrieved);
    }

    [Fact]
    public async Task BatchInsert_MultipleEntities_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var id1 = Guid.NewGuid();
        var id2 = Guid.NewGuid();

        var categories = new[]
        {
            new Category { Id = id1, Name = "DI Category1" },
            new Category { Id = id2, Name = "DI Category2" }
        };

        context.Categories.AddRange(categories);
        await context.SaveChangesAsync();

        var count = await context.Categories
            .Where(c => c.Id == id1 || c.Id == id2)
            .CountAsync();

        Assert.Equal(2, count);
    }

    [Fact]
    public async Task BatchUpdate_MultipleEntities_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var id1 = Guid.NewGuid();
        var id2 = Guid.NewGuid();

        var categories = new[]
        {
            new Category { Id = id1, Name = "DI Cat1" },
            new Category { Id = id2, Name = "DI Cat2" }
        };

        context.Categories.AddRange(categories);
        await context.SaveChangesAsync();

        categories[0].Name = "DI Updated1";
        categories[1].Name = "DI Updated2";
        await context.SaveChangesAsync();

        var retrieved = await context.Categories
            .Where(c => c.Id == id1 || c.Id == id2)
            .ToListAsync();

        Assert.Contains(retrieved, c => c.Name == "DI Updated1");
        Assert.Contains(retrieved, c => c.Name == "DI Updated2");
    }

    [Fact]
    public async Task MixedOperations_InsertUpdateDelete_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var id1 = Guid.NewGuid();
        var id2 = Guid.NewGuid();
        var id3 = Guid.NewGuid();

        var existing = new Category { Id = id1, Name = "DI Existing" };
        var toDelete = new Category { Id = id2, Name = "DI ToDelete" };

        context.Categories.AddRange(existing, toDelete);
        await context.SaveChangesAsync();

        context.Categories.Add(new Category { Id = id3, Name = "DI New" });
        existing.Name = "DI Modified";
        context.Categories.Remove(toDelete);

        await context.SaveChangesAsync();

        var results = await context.Categories
            .Where(c => c.Id == id1 || c.Id == id2 || c.Id == id3)
            .ToListAsync();

        Assert.Equal(2, results.Count);
        Assert.Contains(results, c => c.Name == "DI Modified");
        Assert.Contains(results, c => c.Name == "DI New");
    }
}
