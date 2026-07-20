// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

using System;
using System.Threading.Tasks;
using Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;
using Xunit;

namespace Amazon.AuroraDsql.EntityFrameworkCore.UnitTests;

public class DsqlDatabaseCreatorTests
{
    [Fact]
    public void EnsureCreated_OverrideExists_AndDeclaresOnDsqlDatabaseCreator()
    {
        var method = typeof(DsqlDatabaseCreator).GetMethod(
            nameof(DsqlDatabaseCreator.EnsureCreated), Type.EmptyTypes);

        Assert.NotNull(method);
        Assert.Equal(typeof(DsqlDatabaseCreator), method!.DeclaringType);
    }

    [Fact]
    public void EnsureCreatedAsync_OverrideExists_AndDeclaresOnDsqlDatabaseCreator()
    {
        var method = typeof(DsqlDatabaseCreator).GetMethod(
            nameof(DsqlDatabaseCreator.EnsureCreatedAsync));

        Assert.NotNull(method);
        Assert.Equal(typeof(DsqlDatabaseCreator), method!.DeclaringType);
    }

    [Fact]
    public void EnsureDeleted_OverrideExists_AndDeclaresOnDsqlDatabaseCreator()
    {
        var method = typeof(DsqlDatabaseCreator).GetMethod(
            nameof(DsqlDatabaseCreator.EnsureDeleted), Type.EmptyTypes);

        Assert.NotNull(method);
        Assert.Equal(typeof(DsqlDatabaseCreator), method!.DeclaringType);
    }

    [Fact]
    public void EnsureDeletedAsync_OverrideExists_AndDeclaresOnDsqlDatabaseCreator()
    {
        var method = typeof(DsqlDatabaseCreator).GetMethod(
            nameof(DsqlDatabaseCreator.EnsureDeletedAsync));

        Assert.NotNull(method);
        Assert.Equal(typeof(DsqlDatabaseCreator), method!.DeclaringType);
    }
}