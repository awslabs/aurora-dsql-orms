namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class RawSqlTests : IClassFixture<DsqlTestFixture>
{
    private readonly DsqlTestFixture _fixture;

    public RawSqlTests(DsqlTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task FromSqlInterpolated_ParameterizedQuery_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "SqlTest" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        var results = await context.Categories
            .FromSqlInterpolated($"SELECT * FROM \"Categories\" WHERE \"Name\" = {"SqlTest"}")
            .ToListAsync();

        Assert.Single(results);
        Assert.Equal("SqlTest", results[0].Name);
    }

    [Fact]
    public async Task ExecuteSqlInterpolated_InsertStatement_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var rowsAffected = await context.Database.ExecuteSqlInterpolatedAsync(
            $"INSERT INTO \"Categories\" (\"Id\", \"Name\") VALUES ({categoryId}, {"RawInsert"})");

        Assert.Equal(1, rowsAffected);

        var retrieved = await context.Categories.FindAsync(categoryId);
        Assert.NotNull(retrieved);
        Assert.Equal("RawInsert", retrieved.Name);
    }
}
