// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class PrimaryKeyTests : IClassFixture<DsqlTestFixture>
{
    private readonly DsqlTestFixture _fixture;

    public PrimaryKeyTests(DsqlTestFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task Insert_WithoutSettingId_GeneratesUuid()
    {
        await using var context = _fixture.CreateContext();

        var category = new Category { Name = "AutoGenPK" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        Assert.NotEqual(Guid.Empty, category.Id);

        var retrieved = await context.Categories.FindAsync(category.Id);
        Assert.NotNull(retrieved);
        Assert.Equal("AutoGenPK", retrieved.Name);
    }

    [Fact]
    public async Task Insert_MultipleWithoutId_GeneratesUniqueUuids()
    {
        await using var context = _fixture.CreateContext();

        var cat1 = new Category { Name = "AutoPK1" };
        var cat2 = new Category { Name = "AutoPK2" };
        context.Categories.AddRange(cat1, cat2);
        await context.SaveChangesAsync();

        Assert.NotEqual(Guid.Empty, cat1.Id);
        Assert.NotEqual(Guid.Empty, cat2.Id);
        Assert.NotEqual(cat1.Id, cat2.Id);
    }

    [Fact]
    public async Task Insert_WithExplicitId_UsesProvidedId()
    {
        await using var context = _fixture.CreateContext();

        var explicitId = Guid.NewGuid();
        var category = new Category { Id = explicitId, Name = "ExplicitPK" };
        context.Categories.Add(category);
        await context.SaveChangesAsync();

        Assert.Equal(explicitId, category.Id);

        var retrieved = await context.Categories.FindAsync(explicitId);
        Assert.NotNull(retrieved);
        Assert.Equal("ExplicitPK", retrieved.Name);
    }

    [Fact]
    public async Task Insert_WithIdentityColumn_GeneratesBigintId()
    {
        await using var context = _fixture.CreateContext(dsql => dsql.EnableIdentityColumns());

        var counter = new Counter { Name = "IdentityPK" };
        context.Counters.Add(counter);
        await context.SaveChangesAsync();

        Assert.NotEqual(0L, counter.Id);

        var retrieved = await context.Counters.FindAsync(counter.Id);
        Assert.NotNull(retrieved);
        Assert.Equal("IdentityPK", retrieved.Name);
    }

    [Fact]
    public async Task Insert_MultipleWithIdentity_GeneratesUniqueIds()
    {
        await using var context = _fixture.CreateContext(dsql => dsql.EnableIdentityColumns());

        var c1 = new Counter { Name = "Identity1" };
        var c2 = new Counter { Name = "Identity2" };
        context.Counters.AddRange(c1, c2);
        await context.SaveChangesAsync();

        Assert.NotEqual(0L, c1.Id);
        Assert.NotEqual(0L, c2.Id);
        Assert.NotEqual(c1.Id, c2.Id);
    }
}