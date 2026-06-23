// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class DataTypeTests : IClassFixture<DsqlTestFixture>
{
    private readonly DsqlTestFixture _fixture;

    public DataTypeTests(DsqlTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task RoundTrip_AllSupportedDataTypes_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();
        var productId = Guid.NewGuid();
        var now = DateTime.UtcNow;

        var category = new Category { Id = categoryId, Name = "Test" };
        context.Categories.Add(category);

        var product = new Product
        {
            Id = productId,
            Name = "Test Product",
            Price = 123.45m,
            Stock = 100,
            CreatedAt = now,
            IsActive = true,
            CategoryId = categoryId
        };
        context.Products.Add(product);
        await context.SaveChangesAsync();

        var retrieved = await context.Products.FindAsync(productId);
        Assert.NotNull(retrieved);
        Assert.Equal(productId, retrieved.Id);
        Assert.Equal("Test Product", retrieved.Name);
        Assert.Equal(123.45m, retrieved.Price);
        Assert.Equal(100, retrieved.Stock);
        Assert.True(retrieved.IsActive);
        Assert.Equal(now.ToString("O"), retrieved.CreatedAt.ToString("O"));
    }

    [Fact]
    public async Task RoundTrip_UnicodeString_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "日本語 🎌 Emoji" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        var retrieved = await context.Categories.FindAsync(categoryId);
        Assert.NotNull(retrieved);
        Assert.Equal("日本語 🎌 Emoji", retrieved.Name);
    }

    [Fact]
    public async Task RoundTrip_EmptyString_Succeeds()
    {
        await using var context = _fixture.CreateContext();
        var productId = Guid.NewGuid();
        var categoryId = Guid.NewGuid();

        var category = new Category { Id = categoryId, Name = "Test" };
        context.Categories.Add(category);

        var product = new Product
        {
            Id = productId,
            Name = "",
            Price = 0m,
            CategoryId = categoryId
        };
        context.Products.Add(product);
        await context.SaveChangesAsync();

        var retrieved = await context.Products.FindAsync(productId);
        Assert.NotNull(retrieved);
        Assert.Equal(string.Empty, retrieved.Name);
    }
}