namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class CrudTests : IClassFixture<DsqlTestFixture>
{
    private readonly DsqlTestFixture _fixture;

    public CrudTests(DsqlTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task Insert_SingleEntity_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Electronics" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        var retrieved = await context.Categories.FindAsync(categoryId);
        Assert.NotNull(retrieved);
        Assert.Equal("Electronics", retrieved.Name);
    }

    [Fact]
    public async Task Update_SingleEntity_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Books" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        category.Name = "Audiobooks";
        await context.SaveChangesAsync();

        var retrieved = await context.Categories.FindAsync(categoryId);
        Assert.Equal("Audiobooks", retrieved!.Name);
    }

    [Fact]
    public async Task Delete_SingleEntity_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Obsolete" };
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
            new Category { Id = id1, Name = "Category1" },
            new Category { Id = id2, Name = "Category2" }
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
            new Category { Id = id1, Name = "Cat1" },
            new Category { Id = id2, Name = "Cat2" }
        };

        context.Categories.AddRange(categories);
        await context.SaveChangesAsync();

        categories[0].Name = "Updated1";
        categories[1].Name = "Updated2";
        await context.SaveChangesAsync();

        var retrieved = await context.Categories
            .Where(c => c.Id == id1 || c.Id == id2)
            .ToListAsync();

        Assert.Contains(retrieved, c => c.Name == "Updated1");
        Assert.Contains(retrieved, c => c.Name == "Updated2");
    }

    [Fact]
    public async Task MixedOperations_InsertUpdateDelete_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var id1 = Guid.NewGuid();
        var id2 = Guid.NewGuid();
        var id3 = Guid.NewGuid();

        var existing = new Category { Id = id1, Name = "Existing" };
        var toDelete = new Category { Id = id2, Name = "ToDelete" };

        context.Categories.AddRange(existing, toDelete);
        await context.SaveChangesAsync();

        context.Categories.Add(new Category { Id = id3, Name = "New" });
        existing.Name = "Modified";
        context.Categories.Remove(toDelete);

        await context.SaveChangesAsync();

        var results = await context.Categories
            .Where(c => c.Id == id1 || c.Id == id2 || c.Id == id3)
            .ToListAsync();

        Assert.Equal(2, results.Count);
        Assert.Contains(results, c => c.Name == "Modified");
        Assert.Contains(results, c => c.Name == "New");
    }
}
