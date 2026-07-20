// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

using Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[Collection("DsqlTests")]
public class MigratorTests
{
    private readonly DsqlDiTestFixture _fixture;

    public MigratorTests(DsqlDiTestFixture fixture) => _fixture = fixture;

    [Fact]
    public void Migrate_ResolvesDsqlMigrator()
    {
        using var ctx = _fixture.CreateContext();
        var migrator = ctx.GetService<IMigrator>();

        Assert.NotNull(migrator);
        Assert.IsType<DsqlMigrator>(migrator);
    }

    [Fact]
    public void Migrate_ResolvesDsqlSqlTransform()
    {
        using var ctx = _fixture.CreateContext();
        var transform = ctx.GetService<IDsqlSqlTransform>();

        Assert.NotNull(transform);
        Assert.IsType<DsqlSqlTransform>(transform);
    }
}