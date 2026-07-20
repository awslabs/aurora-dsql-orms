// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

using Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;
using Xunit;

namespace Amazon.AuroraDsql.EntityFrameworkCore.UnitTests;

public class DsqlSqlTransformTests
{
    [Theory]
    [InlineData("CREATE TABLE \"Orders\" (\"Id\" uuid)",
                "CREATE TABLE IF NOT EXISTS \"Orders\" (\"Id\" uuid)")]
    [InlineData("create table foo (x int)",
                "create table IF NOT EXISTS foo (x int)")]
    public void MakeIdempotent_AddsIfNotExistsToCreateTable(string input, string expected)
    {
        Assert.Equal(expected, DsqlSqlTransform.MakeIdempotent(input));
    }

    [Fact]
    public void MakeIdempotent_LeavesExistingIfNotExistsUntouched()
    {
        var sql = "CREATE TABLE IF NOT EXISTS foo (x int)";
        Assert.Equal(sql, DsqlSqlTransform.MakeIdempotent(sql));
    }

    [Fact]
    public void MakeIdempotent_DoesNotTouchNonCreateTable()
    {
        var sql = "ALTER TABLE foo ADD COLUMN y int";
        Assert.Equal(sql, DsqlSqlTransform.MakeIdempotent(sql));
    }

    [Theory]
    [InlineData("CREATE INDEX idx_foo ON bar (col)",
                "CREATE INDEX IF NOT EXISTS idx_foo ON bar (col)")]
    [InlineData("CREATE UNIQUE INDEX idx_foo ON bar (col)",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_foo ON bar (col)")]
    [InlineData("CREATE INDEX ASYNC idx_foo ON bar (col)",
                "CREATE INDEX ASYNC IF NOT EXISTS idx_foo ON bar (col)")]
    [InlineData("CREATE UNIQUE INDEX ASYNC idx_foo ON bar (col)",
                "CREATE UNIQUE INDEX ASYNC IF NOT EXISTS idx_foo ON bar (col)")]
    [InlineData("create index idx_foo ON bar (col)",
                "create index IF NOT EXISTS idx_foo ON bar (col)")]
    public void MakeIdempotent_AddsIfNotExistsToCreateIndex(string input, string expected)
    {
        Assert.Equal(expected, DsqlSqlTransform.MakeIdempotent(input));
    }

    [Fact]
    public void MakeIdempotent_LeavesExistingIfNotExistsIndexUntouched()
    {
        var sql = "CREATE INDEX IF NOT EXISTS idx_foo ON bar (col)";
        Assert.Equal(sql, DsqlSqlTransform.MakeIdempotent(sql));
    }
}