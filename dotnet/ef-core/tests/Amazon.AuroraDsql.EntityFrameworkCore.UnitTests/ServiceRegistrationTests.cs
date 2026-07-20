// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

using System;
using System.Linq;
using Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace Amazon.AuroraDsql.EntityFrameworkCore.UnitTests;

public class ServiceRegistrationTests
{
    [Fact]
    public void ApplyServices_RegistersDsqlSqlTransform()
    {
        var services = new ServiceCollection();
        var extension = new DsqlOptionsExtension();

        extension.ApplyServices(services);

        Assert.Contains(services, d => d.ServiceType == typeof(IDsqlSqlTransform));
    }

    [Fact]
    public void ApplyServices_RegistersDsqlMigrator()
    {
        var services = new ServiceCollection();
        var extension = new DsqlOptionsExtension();

        extension.ApplyServices(services);

        var migratorDescriptors = services
            .Where(d => d.ServiceType == typeof(IMigrator))
            .ToList();
        Assert.Single(migratorDescriptors);
        Assert.Equal(typeof(DsqlMigrator), migratorDescriptors[0].ImplementationType);
    }

    [Theory]
    [InlineData(1)]
    [InlineData(DsqlDbContextOptionsBuilder.DefaultIdentityCacheSize)]
    [InlineData(DsqlDbContextOptionsBuilder.DefaultIdentityCacheSize + 1)]
    public void EnableIdentityColumns_ValidCacheSize_Succeeds(int cacheSize)
    {
        var builder = new DsqlDbContextOptionsBuilder();

        builder.EnableIdentityColumns(cacheSize);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(2)]
    [InlineData(1000)]
    [InlineData(DsqlDbContextOptionsBuilder.DefaultIdentityCacheSize - 1)]
    public void EnableIdentityColumns_InvalidCacheSize_Throws(int cacheSize)
    {
        var builder = new DsqlDbContextOptionsBuilder();

        Assert.Throws<ArgumentOutOfRangeException>(
            () => builder.EnableIdentityColumns(cacheSize));
    }
}