// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

// Tests host-string path independently via Collection, no fixture injection needed
[Collection("DsqlTests")]
public class HostStringTests
{
    [Fact]
    public async Task UseDsql_WithHostString_CanInsertAndRead()
    {
        var endpoint = Environment.GetEnvironmentVariable("CLUSTER_ENDPOINT")
            ?? throw new InvalidOperationException("CLUSTER_ENDPOINT environment variable is required");

        var options = new DbContextOptionsBuilder<TestDbContext>()
            .UseDsql(endpoint)
            .Options;

        await using var context = new TestDbContext(options);

        var categoryId = Guid.NewGuid();
        var category = new Category { Id = categoryId, Name = "HostStringTest" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        var retrieved = await context.Categories.FindAsync(categoryId);
        Assert.NotNull(retrieved);
        Assert.Equal("HostStringTest", retrieved.Name);

        context.Categories.Remove(retrieved);
        await context.SaveChangesAsync();
    }
}