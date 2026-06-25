// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class QueryTests : IClassFixture<DsqlTestFixture>
{
    private readonly DsqlTestFixture _fixture;

    public QueryTests(DsqlTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task Where_WithEqualityAndComparison_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();
        var prodId1 = Guid.NewGuid();
        var prodId2 = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Test" };
        context.Categories.Add(category);

        context.Products.AddRange(
            new Product { Id = prodId1, Name = "Expensive", Price = 100m, CategoryId = categoryId },
            new Product { Id = prodId2, Name = "Cheap", Price = 10m, CategoryId = categoryId }
        );
        await context.SaveChangesAsync();

        var results = await context.Products
            .Where(p => p.Price > 50m && p.Name.Contains("Exp"))
            .ToListAsync();

        Assert.Single(results);
        Assert.Equal("Expensive", results[0].Name);
    }

    [Fact]
    public async Task OrderBy_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Test" };
        context.Categories.Add(category);

        context.Products.AddRange(
            new Product { Id = Guid.NewGuid(), Name = "C", Price = 30m, CategoryId = categoryId },
            new Product { Id = Guid.NewGuid(), Name = "A", Price = 10m, CategoryId = categoryId },
            new Product { Id = Guid.NewGuid(), Name = "B", Price = 20m, CategoryId = categoryId }
        );
        await context.SaveChangesAsync();

        var results = await context.Products
            .Where(p => p.CategoryId == categoryId)
            .OrderBy(p => p.Price)
            .Select(p => p.Name)
            .ToListAsync();

        Assert.Equal(new[] { "A", "B", "C" }, results);
    }

    [Fact]
    public async Task GroupBy_WithAggregation_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var cat1 = Guid.NewGuid();
        var cat2 = Guid.NewGuid();

        context.Categories.AddRange(
            new Category { Id = cat1, Name = "Cat1" },
            new Category { Id = cat2, Name = "Cat2" }
        );

        context.Products.AddRange(
            new Product { Id = Guid.NewGuid(), Name = "P1", Price = 100m, CategoryId = cat1 },
            new Product { Id = Guid.NewGuid(), Name = "P2", Price = 200m, CategoryId = cat1 },
            new Product { Id = Guid.NewGuid(), Name = "P3", Price = 50m, CategoryId = cat2 }
        );
        await context.SaveChangesAsync();

        var results = await context.Products
            .Where(p => p.CategoryId == cat1 || p.CategoryId == cat2)
            .GroupBy(p => p.CategoryId)
            .Select(g => new { CategoryId = g.Key, Total = g.Sum(p => p.Price), Count = g.Count() })
            .ToListAsync();

        Assert.Equal(2, results.Count);
        Assert.Contains(results, r => r.Total == 300m && r.Count == 2);
        Assert.Contains(results, r => r.Total == 50m && r.Count == 1);
    }

    [Fact]
    public async Task SkipTake_Pagination_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Test" };
        context.Categories.Add(category);

        for (int i = 0; i < 10; i++)
        {
            context.Products.Add(new Product
            {
                Id = Guid.NewGuid(),
                Name = $"Product{i}",
                Price = i * 10m,
                CategoryId = categoryId
            });
        }
        await context.SaveChangesAsync();

        var results = await context.Products
            .Where(p => p.CategoryId == categoryId)
            .OrderBy(p => p.Price)
            .Skip(3)
            .Take(3)
            .ToListAsync();

        Assert.Equal(3, results.Count);
        Assert.Equal(30m, results[0].Price);
        Assert.Equal(50m, results[2].Price);
    }

    [Fact]
    public async Task Distinct_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Test" };
        context.Categories.Add(category);

        context.Products.AddRange(
            new Product { Id = Guid.NewGuid(), Name = "A", Price = 10m, CategoryId = categoryId },
            new Product { Id = Guid.NewGuid(), Name = "A", Price = 20m, CategoryId = categoryId },
            new Product { Id = Guid.NewGuid(), Name = "B", Price = 30m, CategoryId = categoryId }
        );
        await context.SaveChangesAsync();

        var names = await context.Products
            .Where(p => p.CategoryId == categoryId)
            .Select(p => p.Name)
            .Distinct()
            .ToListAsync();

        Assert.Equal(2, names.Count);
    }
}