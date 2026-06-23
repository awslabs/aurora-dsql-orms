using System.Data.Common;
using Amazon.AuroraDsql.EntityFrameworkCore.Extensions;
using Microsoft.Extensions.DependencyInjection;

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

/// <summary>
/// Test fixture using DI pattern (AddDsqlDataSource + UseDsql with no args).
/// This is the recommended customer pattern per README.md.
/// </summary>
public class DsqlDiTestFixture : IAsyncLifetime
{
    private ServiceProvider? _serviceProvider;

    public async Task InitializeAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("CLUSTER_ENDPOINT")
            ?? throw new InvalidOperationException("CLUSTER_ENDPOINT environment variable is required");

        var services = new ServiceCollection();

        services.AddDsqlDataSource(endpoint);
        services.AddLogging(logging =>
        {
            logging.AddConsole();
            logging.SetMinimumLevel(LogLevel.Debug);
            logging.AddFilter("Amazon.AuroraDsql.EntityFrameworkCore", LogLevel.Debug);
            logging.AddFilter("Microsoft", LogLevel.Warning);
            logging.AddFilter("Npgsql", LogLevel.Warning);
        });
        services.AddDbContext<TestDbContext>((sp, options) => options.UseDsql(sp));

        _serviceProvider = services.BuildServiceProvider();

        var dataSource = _serviceProvider.GetRequiredService<DbDataSource>();
        await TestSchemaHelper.CreateSchemaAsync(dataSource);
        await TestSchemaHelper.CleanupDataAsync(dataSource);
    }

    public async Task DisposeAsync()
    {
        if (_serviceProvider != null)
        {
            await _serviceProvider.DisposeAsync();
        }
    }

    public TestDbContext CreateContext()
    {
        if (_serviceProvider == null)
            throw new InvalidOperationException("Service provider not initialized");

        // Scope leaks but is cleaned up when _serviceProvider disposes at fixture teardown.
        var scope = _serviceProvider.CreateScope();
        return scope.ServiceProvider.GetRequiredService<TestDbContext>();
    }
}
