// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

namespace Amazon.AuroraDsql.EntityFrameworkCore.Extensions;

/// <summary>
/// Extension methods for configuring DSQL services in IServiceCollection.
/// </summary>
public static class DsqlServiceCollectionExtensions
{
    private static void RegisterWrappingDataSource(IServiceCollection services)
    {
        services.AddSingleton<DbDataSource>(sp =>
        {
            var dsqlDataSource = sp.GetRequiredService<DsqlDataSource>();
            var loggerFactory = sp.GetService<ILoggerFactory>();
            return new DsqlWrappingDataSource(dsqlDataSource.DataSource, loggerFactory);
        });
    }

    /// <summary>
    /// Registers a singleton DsqlDataSource and DbDataSource in the DI container.
    /// Uses sync-over-async. For deadlock-safe registration, use the overload accepting a pre-created DsqlDataSource.
    /// </summary>
    public static IServiceCollection AddDsqlDataSource(
        this IServiceCollection services,
        string host)
    {
        if (services == null)
            throw new ArgumentNullException(nameof(services));

        if (string.IsNullOrWhiteSpace(host))
            throw new ArgumentException("Host cannot be empty.", nameof(host));

        services.AddSingleton(sp =>
        {
            var config = new DsqlConfig { Host = host };
            return DsqlDataSource.CreateAsync(config).GetAwaiter().GetResult();
        });

        RegisterWrappingDataSource(services);

        return services;
    }

    /// <summary>
    /// Registers a singleton DsqlDataSource with custom configuration.
    /// Uses sync-over-async. For deadlock-safe registration, use the overload accepting a pre-created DsqlDataSource.
    /// </summary>
    public static IServiceCollection AddDsqlDataSource(
        this IServiceCollection services,
        string host,
        Action<DsqlConfig> configureOptions)
    {
        if (services == null)
            throw new ArgumentNullException(nameof(services));

        if (string.IsNullOrWhiteSpace(host))
            throw new ArgumentException("Host cannot be empty.", nameof(host));

        if (configureOptions == null)
            throw new ArgumentNullException(nameof(configureOptions));

        services.AddSingleton(sp =>
        {
            var config = new DsqlConfig { Host = host };
            configureOptions(config);
            return DsqlDataSource.CreateAsync(config).GetAwaiter().GetResult();
        });

        RegisterWrappingDataSource(services);

        return services;
    }

    /// <summary>
    /// Registers a pre-created DsqlDataSource instance. Avoids sync-over-async blocking.
    /// </summary>
    public static IServiceCollection AddDsqlDataSource(
        this IServiceCollection services,
        DsqlDataSource dsqlDataSource)
    {
        if (services == null)
            throw new ArgumentNullException(nameof(services));

        if (dsqlDataSource == null)
            throw new ArgumentNullException(nameof(dsqlDataSource));

        services.AddSingleton(dsqlDataSource);

        RegisterWrappingDataSource(services);

        return services;
    }
}