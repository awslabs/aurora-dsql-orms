// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class ConnectionLifecycleTests : IClassFixture<DsqlTestFixture>
{
    private readonly DsqlTestFixture _fixture;

    public ConnectionLifecycleTests(DsqlTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task CreateAndDispose_ManyContexts_DoesNotExhaustConnections()
    {
        for (int i = 0; i < 50; i++)
        {
            await using var context = _fixture.CreateContext();
            var categoryId = Guid.NewGuid();

            var category = new Category { Id = categoryId, Name = $"Test{i}" };
            context.Categories.Add(category);
            await context.SaveChangesAsync();

            var retrieved = await context.Categories.FindAsync(categoryId);
            Assert.NotNull(retrieved);
        }
    }

    [Fact]
    public async Task ContextDispose_DisposesConnection()
    {
        var context = _fixture.CreateContext();
        var categoryId = Guid.NewGuid();

        context.Categories.Add(new Category { Id = categoryId, Name = "Test" });
        await context.SaveChangesAsync();

        await context.DisposeAsync();

        Assert.Throws<ObjectDisposedException>(() => context.Categories.Add(new Category()));
    }
}