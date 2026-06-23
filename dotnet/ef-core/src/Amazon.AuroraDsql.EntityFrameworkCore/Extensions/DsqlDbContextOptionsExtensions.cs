// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

using Microsoft.EntityFrameworkCore.Infrastructure;

namespace Amazon.AuroraDsql.EntityFrameworkCore.Extensions;

/// <summary>
/// Extension methods for configuring DbContextOptions to use DSQL.
/// </summary>
public static class DsqlDbContextOptionsExtensions
{
    /// <summary>
    /// Configures the context to connect to Aurora DSQL using the DI-registered DbDataSource.
    /// </summary>
    public static DbContextOptionsBuilder UseDsql(
        this DbContextOptionsBuilder optionsBuilder,
        IServiceProvider serviceProvider,
        Action<DsqlDbContextOptionsBuilder>? dsqlOptionsAction = null)
    {
        if (optionsBuilder == null)
            throw new ArgumentNullException(nameof(optionsBuilder));

        if (serviceProvider == null)
            throw new ArgumentNullException(nameof(serviceProvider));

        var dataSource = serviceProvider.GetRequiredService<DbDataSource>();
        var dsqlOptions = ResolveDsqlOptions(dsqlOptionsAction);
        optionsBuilder.UseNpgsql(dataSource, npgsql =>
            npgsql.ExecutionStrategy(deps => new DsqlExecutionStrategy(deps, dsqlOptions.MaxRetryCount, dsqlOptions.MaxRetryDelay)));
        AddDsqlExtension(optionsBuilder, dsqlOptions);

        return optionsBuilder;
    }

    /// <summary>
    /// Configures the context to connect to Aurora DSQL using a host string.
    /// Uses sync-over-async. For deadlock-safe initialization, register a pre-created
    /// DsqlDataSource via AddDsqlDataSource(DsqlDataSource) and use UseDsql(IServiceProvider).
    /// </summary>
    public static DbContextOptionsBuilder UseDsql(
        this DbContextOptionsBuilder optionsBuilder,
        string host,
        ILoggerFactory? loggerFactory = null,
        Action<DsqlDbContextOptionsBuilder>? dsqlOptionsAction = null)
    {
        if (optionsBuilder == null)
            throw new ArgumentNullException(nameof(optionsBuilder));

        if (string.IsNullOrWhiteSpace(host))
            throw new ArgumentException("Host cannot be empty.", nameof(host));

        var config = new DsqlConfig { Host = host };
        var dataSource = DsqlDataSource.CreateAsync(config).GetAwaiter().GetResult();

        return UseDsql(optionsBuilder, dataSource, loggerFactory, dsqlOptionsAction);
    }

    /// <summary>
    /// Configures the context to connect to Aurora DSQL using a pre-configured DsqlDataSource.
    /// </summary>
    public static DbContextOptionsBuilder UseDsql(
        this DbContextOptionsBuilder optionsBuilder,
        DsqlDataSource dsqlDataSource,
        ILoggerFactory? loggerFactory = null,
        Action<DsqlDbContextOptionsBuilder>? dsqlOptionsAction = null)
    {
        if (optionsBuilder == null)
            throw new ArgumentNullException(nameof(optionsBuilder));

        if (dsqlDataSource == null)
            throw new ArgumentNullException(nameof(dsqlDataSource));

        var wrappingDataSource = new DsqlWrappingDataSource(dsqlDataSource.DataSource, loggerFactory);
        var dsqlOptions = ResolveDsqlOptions(dsqlOptionsAction);
        optionsBuilder.UseNpgsql(wrappingDataSource, npgsql =>
            npgsql.ExecutionStrategy(deps => new DsqlExecutionStrategy(deps, dsqlOptions.MaxRetryCount, dsqlOptions.MaxRetryDelay)));
        AddDsqlExtension(optionsBuilder, dsqlOptions);

        return optionsBuilder;
    }

    /// <summary>
    /// Configures the context to connect to Aurora DSQL using the DI-registered DbDataSource (generic version).
    /// </summary>
    public static DbContextOptionsBuilder<TContext> UseDsql<TContext>(
        this DbContextOptionsBuilder<TContext> optionsBuilder,
        IServiceProvider serviceProvider,
        Action<DsqlDbContextOptionsBuilder>? dsqlOptionsAction = null)
        where TContext : DbContext
    {
        return (DbContextOptionsBuilder<TContext>)UseDsql((DbContextOptionsBuilder)optionsBuilder, serviceProvider, dsqlOptionsAction);
    }

    /// <summary>
    /// Configures the context to connect to Aurora DSQL using a host string (generic version).
    /// </summary>
    public static DbContextOptionsBuilder<TContext> UseDsql<TContext>(
        this DbContextOptionsBuilder<TContext> optionsBuilder,
        string host,
        ILoggerFactory? loggerFactory = null,
        Action<DsqlDbContextOptionsBuilder>? dsqlOptionsAction = null)
        where TContext : DbContext
    {
        return (DbContextOptionsBuilder<TContext>)UseDsql((DbContextOptionsBuilder)optionsBuilder, host, loggerFactory, dsqlOptionsAction);
    }

    /// <summary>
    /// Configures the context to connect to Aurora DSQL using a data source (generic version).
    /// </summary>
    public static DbContextOptionsBuilder<TContext> UseDsql<TContext>(
        this DbContextOptionsBuilder<TContext> optionsBuilder,
        DsqlDataSource dsqlDataSource,
        ILoggerFactory? loggerFactory = null,
        Action<DsqlDbContextOptionsBuilder>? dsqlOptionsAction = null)
        where TContext : DbContext
    {
        return (DbContextOptionsBuilder<TContext>)UseDsql((DbContextOptionsBuilder)optionsBuilder, dsqlDataSource, loggerFactory, dsqlOptionsAction);
    }

    private static void AddDsqlExtension(DbContextOptionsBuilder optionsBuilder, ResolvedDsqlOptions dsqlOptions)
    {
        var extension = new DsqlOptionsExtension
        {
            UseIdentityColumns = dsqlOptions.UseIdentityColumns,
            IdentityCacheSize = dsqlOptions.IdentityCacheSize
        };
        ((IDbContextOptionsBuilderInfrastructure)optionsBuilder).AddOrUpdateExtension(extension);
    }

    private static ResolvedDsqlOptions ResolveDsqlOptions(Action<DsqlDbContextOptionsBuilder>? dsqlOptionsAction)
    {
        var builder = new DsqlDbContextOptionsBuilder();
        dsqlOptionsAction?.Invoke(builder);

        return new ResolvedDsqlOptions
        {
            MaxRetryCount = builder.MaxRetryCount ?? DsqlExecutionStrategy.DefaultMaxRetryCount,
            MaxRetryDelay = builder.MaxRetryDelay ?? DsqlExecutionStrategy.DefaultMaxRetryDelay,
            UseIdentityColumns = builder.UseIdentityColumns,
            IdentityCacheSize = builder.IdentityCacheSize
        };
    }

    private struct ResolvedDsqlOptions
    {
        public int MaxRetryCount;
        public TimeSpan MaxRetryDelay;
        public bool UseIdentityColumns;
        public int IdentityCacheSize;
    }
}