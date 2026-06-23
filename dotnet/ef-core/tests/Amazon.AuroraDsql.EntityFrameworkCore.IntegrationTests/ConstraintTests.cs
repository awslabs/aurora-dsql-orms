using Npgsql;

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class ConstraintTests : IClassFixture<DsqlTestFixture>
{
    private readonly DsqlTestFixture _fixture;

    public ConstraintTests(DsqlTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task DuplicatePrimaryKey_ThrowsException()
    {
        var categoryId = Guid.NewGuid();

        // Insert first category
        await using (var context = _fixture.CreateContext())
        {
            context.Categories.Add(new Category { Id = categoryId, Name = "First" });
            await context.SaveChangesAsync();
        }

        // Simulate concurrent write: new context tries to insert same ID
        // (This is what happens in real concurrent scenarios)
        await using (var context = _fixture.CreateContext())
        {
            context.Categories.Add(new Category { Id = categoryId, Name = "Duplicate" });

            var exception = await Assert.ThrowsAsync<DbUpdateException>(
                async () => await context.SaveChangesAsync());

            var pgException = exception.InnerException as PostgresException;
            Assert.NotNull(pgException);
            Assert.Equal("23505", pgException.SqlState); // Unique violation
        }
    }

    [Fact]
    public async Task NotNullConstraintViolation_ThrowsException()
    {
        await using var context = _fixture.CreateContext();

        // Try to save entity with null required field
        var category = new Category { Id = Guid.NewGuid(), Name = null! };
        context.Categories.Add(category);

        var exception = await Assert.ThrowsAsync<DbUpdateException>(
            async () => await context.SaveChangesAsync());

        var pgException = exception.InnerException as PostgresException;
        Assert.NotNull(pgException);
        Assert.Equal("23502", pgException.SqlState); // NOT NULL violation
    }
}
