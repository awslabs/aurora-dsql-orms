// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

using Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql;

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

/// <summary>
/// End-to-end migration test exercising the full DsqlMigrator pipeline against a real cluster.
///
/// Uses hand-written Migration classes (discovered by EF Core's IMigrationsAssembly) to:
/// 1. Apply migration 1 → CREATE TABLE MigTestOrders (DDL transformed by DsqlMigrator pipeline)
/// 2. Insert data into MigTestOrders
/// 3. Apply migration 2 → CREATE TABLE MigTestOrderItems
/// 4. Insert data into MigTestOrderItems
/// 5. Verify both tables have data
/// 6. Cleanup on dispose
/// </summary>
[Collection("DsqlTests")]
public class MigrationEndToEndTests : IClassFixture<DsqlTestFixture>, IAsyncLifetime
{
    private readonly DsqlTestFixture _fixture;

    public MigrationEndToEndTests(DsqlTestFixture fixture) => _fixture = fixture;

    public Task InitializeAsync() => DropTablesAsync();

    public async Task DisposeAsync() => await DropTablesAsync();

    [Fact]
    public async Task Migrate_CreatesTable_InsertsData_ThenAddsSecondTable()
    {
        // Phase 1: Apply first migration
        var options1 = BuildOptions<MigrationTestV1Context>();
        await using (var ctx = new MigrationTestV1Context(options1))
        {
            await ctx.Database.MigrateAsync();

            // Verify the migrator used is ours
            var migrator = ctx.GetService<IMigrator>();
            Assert.IsType<DsqlMigrator>(migrator);
        }

        // Insert data into MigTestOrders
        await using (var ctx = new MigrationTestV1Context(options1))
        {
            ctx.Orders.Add(new MigTestOrder { Description = "First order" });
            await ctx.SaveChangesAsync();
        }

        // Verify data
        await using (var ctx = new MigrationTestV1Context(options1))
        {
            var orders = await ctx.Orders.ToListAsync();
            Assert.Single(orders);
            Assert.Equal("First order", orders[0].Description);
        }

        // Phase 2: Apply second migration (adds MigTestOrderItems)
        var options2 = BuildOptions<MigrationTestV2Context>();
        await using (var ctx = new MigrationTestV2Context(options2))
        {
            await ctx.Database.MigrateAsync();
        }

        // Insert into MigTestOrderItems
        Guid orderId;
        await using (var ctx = new MigrationTestV2Context(options2))
        {
            orderId = await ctx.Orders.Select(o => o.Id).FirstAsync();
            ctx.OrderItems.Add(new MigTestOrderItem
            {
                OrderId = orderId,
                ProductName = "Widget",
                Quantity = 3,
            });
            await ctx.SaveChangesAsync();
        }

        // Verify both tables
        await using (var ctx = new MigrationTestV2Context(options2))
        {
            var orders = await ctx.Orders.ToListAsync();
            var items = await ctx.OrderItems.ToListAsync();

            Assert.Single(orders);
            Assert.Single(items);
            Assert.Equal(orderId, items[0].OrderId);
            Assert.Equal("Widget", items[0].ProductName);
            Assert.Equal(3, items[0].Quantity);
        }
    }

    [Fact]
    public async Task Migrate_IsIdempotent_SecondRunDoesNotFail()
    {
        var options = BuildOptions<MigrationTestV1Context>();

        await using (var ctx = new MigrationTestV1Context(options))
        {
            await ctx.Database.MigrateAsync();
        }

        // Re-run — should not throw (IF NOT EXISTS makes DDL safe to repeat,
        // and __EFMigrationsHistory prevents re-execution anyway)
        await using (var ctx = new MigrationTestV1Context(options))
        {
            await ctx.Database.MigrateAsync();
        }
    }

    private DbContextOptions<T> BuildOptions<T>() where T : DbContext
    {
        return new DbContextOptionsBuilder<T>()
            .UseDsql(_fixture.DataSource)
            .Options;
    }

    private async Task DropTablesAsync()
    {
        const int maxRetries = 5;
        for (var attempt = 0; attempt <= maxRetries; attempt++)
        {
            try
            {
                await using var conn = _fixture.DataSource.DataSource.CreateConnection();
                await conn.OpenAsync();
                await using var cmd = conn.CreateCommand();

                cmd.CommandText = "DROP TABLE IF EXISTS \"MigTestOrderItems\"";
                await cmd.ExecuteNonQueryAsync();

                cmd.CommandText = "DROP TABLE IF EXISTS \"MigTestOrders\"";
                await cmd.ExecuteNonQueryAsync();

                cmd.CommandText = """
                    DELETE FROM "__EFMigrationsHistory"
                    WHERE "MigrationId" LIKE '%MigTest%'
                    """;
                try { await cmd.ExecuteNonQueryAsync(); }
                catch (PostgresException) { /* table may not exist */ }
                return;
            }
            catch (PostgresException ex) when (ex.SqlState == "40001" && attempt < maxRetries)
            {
                await Task.Delay(500 * (attempt + 1));
            }
        }
    }
}

// --- Models ---

public class MigTestOrder
{
    public Guid Id { get; set; }
    public string Description { get; set; } = string.Empty;
}

public class MigTestOrderItem
{
    public Guid Id { get; set; }
    public Guid OrderId { get; set; }
    public string ProductName { get; set; } = string.Empty;
    public int Quantity { get; set; }
}

// --- V1 Context: only MigTestOrders ---

public class MigrationTestV1Context : DbContext
{
    public MigrationTestV1Context(DbContextOptions<MigrationTestV1Context> options) : base(options) { }

    public DbSet<MigTestOrder> Orders => Set<MigTestOrder>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<MigTestOrder>(e =>
        {
            e.ToTable("MigTestOrders");
            e.HasKey(x => x.Id);
            e.Property(x => x.Description).IsRequired().HasMaxLength(500);
        });
    }
}

// --- V2 Context: MigTestOrders + MigTestOrderItems ---

public class MigrationTestV2Context : DbContext
{
    public MigrationTestV2Context(DbContextOptions<MigrationTestV2Context> options) : base(options) { }

    public DbSet<MigTestOrder> Orders => Set<MigTestOrder>();
    public DbSet<MigTestOrderItem> OrderItems => Set<MigTestOrderItem>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<MigTestOrder>(e =>
        {
            e.ToTable("MigTestOrders");
            e.HasKey(x => x.Id);
            e.Property(x => x.Description).IsRequired().HasMaxLength(500);
        });

        modelBuilder.Entity<MigTestOrderItem>(e =>
        {
            e.ToTable("MigTestOrderItems");
            e.HasKey(x => x.Id);
            e.Property(x => x.ProductName).IsRequired().HasMaxLength(200);
        });
    }
}

// --- Migration classes (discovered by EF Core's IMigrationsAssembly) ---

[DbContext(typeof(MigrationTestV1Context))]
[Migration("20260101000001_MigTestCreateOrders")]
public class MigTestCreateOrders : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "MigTestOrders",
            columns: table => new
            {
                Id = table.Column<Guid>(nullable: false, defaultValueSql: "gen_random_uuid()"),
                Description = table.Column<string>(maxLength: 500, nullable: false),
            },
            constraints: table => table.PrimaryKey("PK_MigTestOrders", x => x.Id));
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropTable("MigTestOrders");
    }
}

[DbContext(typeof(MigrationTestV2Context))]
[Migration("20260101000001_MigTestCreateOrders_V2")]
public class MigTestCreateOrdersV2 : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "MigTestOrders",
            columns: table => new
            {
                Id = table.Column<Guid>(nullable: false, defaultValueSql: "gen_random_uuid()"),
                Description = table.Column<string>(maxLength: 500, nullable: false),
            },
            constraints: table => table.PrimaryKey("PK_MigTestOrders", x => x.Id));
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropTable("MigTestOrders");
    }
}

[DbContext(typeof(MigrationTestV2Context))]
[Migration("20260101000002_MigTestCreateOrderItems")]
public class MigTestCreateOrderItems : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "MigTestOrderItems",
            columns: table => new
            {
                Id = table.Column<Guid>(nullable: false, defaultValueSql: "gen_random_uuid()"),
                OrderId = table.Column<Guid>(nullable: false),
                ProductName = table.Column<string>(maxLength: 200, nullable: false),
                Quantity = table.Column<int>(nullable: false),
            },
            constraints: table =>
            {
                table.PrimaryKey("PK_MigTestOrderItems", x => x.Id);
                table.ForeignKey(
                    name: "FK_MigTestOrderItems_MigTestOrders_OrderId",
                    column: x => x.OrderId,
                    principalTable: "MigTestOrders",
                    principalColumn: "Id",
                    onDelete: ReferentialAction.Restrict);
            });

        migrationBuilder.CreateIndex(
            name: "IX_MigTestOrderItems_OrderId",
            table: "MigTestOrderItems",
            column: "OrderId");
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropTable("MigTestOrderItems");
    }
}