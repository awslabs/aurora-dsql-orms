using Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;
using Amazon.AuroraDsql.Npgsql;
using Microsoft.Extensions.Logging;

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

public class DsqlTestFixture : IAsyncLifetime
{
    private DsqlDataSource? _dataSource;
    private ILoggerFactory? _loggerFactory;

    public DsqlDataSource DataSource => _dataSource ?? throw new InvalidOperationException("Fixture not initialized");

    public async Task InitializeAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("CLUSTER_ENDPOINT")
            ?? throw new InvalidOperationException("CLUSTER_ENDPOINT environment variable is required");

        var config = new DsqlConfig { Host = endpoint };
        _dataSource = await DsqlDataSource.CreateAsync(config);

        _loggerFactory = LoggerFactory.Create(builder =>
        {
            builder.AddConsole();
            builder.SetMinimumLevel(LogLevel.Debug);
            builder.AddFilter("Amazon.AuroraDsql.EntityFrameworkCore", LogLevel.Debug);
            builder.AddFilter("Microsoft", LogLevel.Warning);
            builder.AddFilter("Npgsql", LogLevel.Warning);
        });

        await TestSchemaHelper.CreateSchemaAsync(_dataSource.DataSource);
        await TestSchemaHelper.CleanupDataAsync(_dataSource.DataSource);
    }

    public async Task DisposeAsync()
    {
        _loggerFactory?.Dispose();
        if (_dataSource != null)
        {
            await _dataSource.DisposeAsync();
        }
    }

    public TestDbContext CreateContext()
    {
        var options = new DbContextOptionsBuilder<TestDbContext>()
            .UseDsql(DataSource, _loggerFactory)
            .Options;

        return new TestDbContext(options);
    }

    public TestDbContext CreateContext(Action<DsqlDbContextOptionsBuilder> dsqlOptionsAction)
    {
        var options = new DbContextOptionsBuilder<TestDbContext>()
            .UseDsql(DataSource, _loggerFactory, dsqlOptionsAction)
            .Options;

        return new TestDbContext(options);
    }
}
