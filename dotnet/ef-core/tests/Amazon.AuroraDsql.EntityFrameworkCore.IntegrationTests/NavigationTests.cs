// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class NavigationTests : IClassFixture<DsqlTestFixture>
{
    private readonly DsqlTestFixture _fixture;

    public NavigationTests(DsqlTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task Include_EagerLoading_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Electronics" };
        context.Categories.Add(category);

        context.Products.AddRange(
            new Product { Id = Guid.NewGuid(), Name = "Laptop", Price = 1000m, CategoryId = categoryId },
            new Product { Id = Guid.NewGuid(), Name = "Mouse", Price = 20m, CategoryId = categoryId }
        );
        await context.SaveChangesAsync();

        var retrieved = await context.Categories
            .Include(c => c.Products)
            .FirstOrDefaultAsync(c => c.Id == categoryId);

        Assert.NotNull(retrieved);
        Assert.Equal(2, retrieved.Products.Count);
    }

    [Fact]
    public async Task NavigationProperty_InWhere_ImplicitJoin_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Books" };
        context.Categories.Add(category);

        context.Products.Add(new Product
        {
            Id = Guid.NewGuid(),
            Name = "Novel",
            Price = 15m,
            CategoryId = categoryId
        });
        await context.SaveChangesAsync();

        var products = await context.Products
            .Where(p => p.Category!.Name == "Books")
            .ToListAsync();

        Assert.Single(products);
        Assert.Equal("Novel", products[0].Name);
    }

    [Fact]
    public async Task Include_WithEmptyCollection_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Empty" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        var retrieved = await context.Categories
            .Include(c => c.Products)
            .FirstOrDefaultAsync(c => c.Id == categoryId);

        Assert.NotNull(retrieved);
        Assert.Empty(retrieved.Products);
    }
}