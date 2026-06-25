# Amazon Aurora DSQL Adapter for Entity Framework Core

[![GitHub](https://img.shields.io/badge/github-awslabs/aurora--dsql--orms-blue?logo=github)](https://github.com/awslabs/aurora-dsql-orms)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Discord](https://img.shields.io/discord/1435027294837276802.svg?logo=discord)](https://discord.com/invite/nEF6ksFWru)

## Introduction
The Aurora DSQL EF Core adapter integrates Entity Framework Core with Aurora DSQL, enabling .NET applications to use EF Core ORM features with Aurora DSQL’s distributed, highly available architecture.

## Features and Limitations

Aurora DSQL's distributed architecture differs from single-node PostgreSQL
in a few ways that shape how the adapter behaves:

- **Command Suppression** — Filters commands DSQL doesn't support
  (`SET TRANSACTION ISOLATION LEVEL`, `SAVEPOINT`, `LOCK TABLE`) at the
  ADO.NET layer, logged at Debug level. Batch `SaveChanges` works seamlessly.
- **Concurrency Control** — DSQL uses a single optimistic concurrency control
  isolation level; requested isolation levels are ignored. Conflicting
  transactions are retried automatically. See [Concurrency Control](#concurrency-control).
- **Migrations** — DSQL applies one DDL statement per transaction, so a
  multi-statement migration is not applied atomically. The adapter makes DDL
  idempotent (`CREATE TABLE IF NOT EXISTS`) so a migration can be safely re-run
  after fixing a failure. See [Migrations](#migrations).
- **Referential Integrity** — DSQL does not enforce foreign keys; navigation
  properties, `Include`, and joins work normally, but consistency is enforced
  in your application layer.

## Sample Application

A runnable [Inventory API example](examples/InventoryApi) demonstrates CRUD,
batch operations, OCC retry, navigation properties, and migrations against a
live Aurora DSQL cluster. See its [README](examples/InventoryApi#readme) to run it.

## Prerequisites

- .NET 8.0+
- Entity Framework Core 9.0.7+
- Amazon Aurora DSQL cluster
- Amazon.AuroraDsql.Npgsql 1.1.0+

## Setup

```bash
dotnet add package Amazon.AuroraDsql.EntityFrameworkCore
```

Configure your `DbContext` with the `UseDsql()` extension method.

**With DI (ASP.NET Core):**
```csharp
using Amazon.AuroraDsql.EntityFrameworkCore.Extensions;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDsqlDataSource(
    "your-cluster.dsql.us-east-1.on.aws");
builder.Services.AddDbContext<MyDbContext>(
    (sp, options) => options.UseDsql(sp));
```

**Without DI:**
```csharp
using Amazon.AuroraDsql.Npgsql;
using Amazon.AuroraDsql.EntityFrameworkCore.Extensions;

var config = new DsqlConfig
{
    Host = "your-cluster.dsql.us-east-1.on.aws"
};
var dataSource = await DsqlDataSource.CreateAsync(config);

var options = new DbContextOptionsBuilder<MyDbContext>()
    .UseDsql(dataSource)
    .Options;

await using var context = new MyDbContext(options);
```

**DbContext:**
```csharp
public class MyDbContext : DbContext
{
    public MyDbContext(
        DbContextOptions<MyDbContext> options)
        : base(options) { }

    public DbSet<Product> Products { get; set; }
}
```

See [EF Core configuration docs](https://learn.microsoft.com/ef/core/dbcontext-configuration/)
for more options.

### Database Connection

The adapter uses
[Amazon.AuroraDsql.Npgsql](https://github.com/awslabs/aurora-dsql-connectors/tree/main/dotnet/npgsql)
for connection management with automatic IAM authentication.

### Migrations

Standard EF Core migration commands work with Aurora DSQL:

```bash
dotnet ef migrations add CreateOrders
dotnet ef database update
```

The adapter uses [dsql-lint](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint) to transform
EF Core-generated DDL into DSQL-compatible SQL (e.g. `CREATE INDEX` →
`CREATE INDEX ASYNC`).

DSQL applies one DDL statement per transaction, so the adapter makes each
migration statement idempotent (`CREATE TABLE IF NOT EXISTS`). If a migration
fails partway through, fix the cause and re-run `dotnet ef database update` —
already-applied statements are skipped safely.

### Concurrency Control

DSQL uses Optimistic Concurrency Control (OCC). Conflicting transactions
are rejected with SqlState `40001`. The adapter includes
`DsqlExecutionStrategy` which provides automatic OCC retry with
exponential backoff and jitter.

When retries are exhausted, `RetryLimitExceededException` is thrown
wrapping the final `PostgresException`.

**Implicit transactions** — `SaveChangesAsync` is automatically retried:
```csharp
await context.SaveChangesAsync();
```

**Explicit transactions** — use `ExecuteInTransactionAsync` to get OCC retry.
Call `ctx.ChangeTracker.Clear()` at the start of the operation so a retry
doesn't replay stale tracked entities, and pass a verify function that
confirms the commit. See the `/orders` handler in the
[Inventory API example](examples/InventoryApi) for a complete implementation.

> **Note:** Unlike SQL Server's execution strategy, `SaveChangesAsync`
> inside an explicit transaction does not throw — it executes without
> retry. Use `ExecuteInTransactionAsync` for full OCC retry support.

### Primary Keys

`Guid` keys are recommended. The adapter configures a `gen_random_uuid()`
database default, so EF Core treats the key as store-generated — you leave
`Id` unset and DSQL populates it on insert:

```csharp
public class Product
{
    public Guid Id { get; set; }  // populated by DSQL on insert
    public string Name { get; set; }
}
```

For auto-incrementing `long` keys, enable BIGINT IDENTITY columns. DSQL
accepts a cache size of `1` (closer to strict ordering) or `>= 65536`
(higher throughput, default):

```csharp
options.UseDsql(sp, dsql => dsql.EnableIdentityColumns());
// or prioritize ordering over throughput:
options.UseDsql(sp, dsql => dsql.EnableIdentityColumns(cacheSize: 1));
```

Migrations generate the matching DDL automatically. If you manage the schema
outside migrations, include the same defaults — `DEFAULT gen_random_uuid()`
for UUID keys and `GENERATED BY DEFAULT AS IDENTITY (CACHE n)` for IDENTITY
keys.

## Development

Requires a DSQL cluster and AWS credentials
(see [Authentication](#authentication-issues)).

```bash
export CLUSTER_ENDPOINT=your-cluster.dsql.us-east-1.on.aws

dotnet test dotnet/ef-core/tests/\
Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests/
```

## Troubleshooting

### Authentication Issues

Credentials resolve via the AWS SDK default chain:

1. Environment variables (`AWS_ACCESS_KEY_ID`,
   `AWS_SECRET_ACCESS_KEY`)
2. Named profile (`~/.aws/credentials`)
3. IAM role (EC2, ECS, Lambda)

Environment variables:
```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
```

Named profile:
```csharp
services.AddDsqlDataSource(
    "your-cluster.dsql.us-east-1.on.aws",
    config => config.Profile = "AwsProfile");
```

### Logging

The adapter logs under the `Amazon.AuroraDsql.EntityFrameworkCore`
category. Enable `Debug` for that category to see adapter activity such as
suppressed commands and ignored isolation levels:

```csharp
builder.Services.AddLogging(logging =>
    logging.AddFilter(
        "Amazon.AuroraDsql.EntityFrameworkCore",
        LogLevel.Debug));
```

For example, requesting an isolation level logs that DSQL ignored it:
```
warn: Amazon.AuroraDsql.EntityFrameworkCore.Transaction[100002]
      DSQL uses fixed OCC isolation.
      Requested isolation level Serializable is ignored.
```

## Resources

- [Aurora DSQL docs](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html)
- [Concurrency control](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-concurrency-control.html)
- [Unsupported PG features](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-unsupported-features.html)
- [Sequences & identity columns](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/sequences-identity-columns-working-with.html)
- [Aurora DSQL Tools](https://github.com/awslabs/aurora-dsql-tools)
- [dsql-lint](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint)
- [EF Core docs](https://learn.microsoft.com/ef/core/)
- [Amazon.AuroraDsql.Npgsql](https://github.com/awslabs/aurora-dsql-connectors/tree/main/dotnet/npgsql)

## License

Apache-2.0
