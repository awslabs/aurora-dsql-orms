using Microsoft.AspNetCore.Mvc.Testing;

namespace InventoryApi.IntegrationTests;

public class InventoryApiFixture : IAsyncLifetime
{
    private WebApplicationFactory<Program> _factory = default!;
    public HttpClient Client { get; private set; } = default!;

    public Task InitializeAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("CLUSTER_ENDPOINT")
            ?? throw new InvalidOperationException("CLUSTER_ENDPOINT environment variable is required.");

        _factory = new WebApplicationFactory<Program>()
            .WithWebHostBuilder(builder =>
            {
                builder.UseSetting("CLUSTER_ENDPOINT", endpoint);
            });

        Client = _factory.CreateClient();
        return Task.CompletedTask;
    }

    public async Task DisposeAsync()
    {
        Client?.Dispose();
        if (_factory is not null)
            await _factory.DisposeAsync();
    }
}

[CollectionDefinition("InventoryApi")]
public class InventoryApiCollection : ICollectionFixture<InventoryApiFixture> { }
