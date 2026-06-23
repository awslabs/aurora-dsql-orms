// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma warning disable EF1001 // Internal EF Core API usage

using System.Collections.Generic;
using System.Linq;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.EntityFrameworkCore.Migrations.Internal;

namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

internal sealed class DsqlMigrator : Migrator
{
    private readonly IRawSqlCommandBuilder _rawSqlCommandBuilder;
    private readonly IDsqlSqlTransform _transform;
    private readonly ICurrentDbContext _currentContext;
    private readonly IRelationalCommandDiagnosticsLogger _commandLogger;
    private readonly IDiagnosticsLogger<DbLoggerCategory.Migrations> _logger;

    public DsqlMigrator(
        IMigrationsAssembly migrationsAssembly,
        IHistoryRepository historyRepository,
        IDatabaseCreator databaseCreator,
        IMigrationsSqlGenerator migrationsSqlGenerator,
        IRawSqlCommandBuilder rawSqlCommandBuilder,
        IMigrationCommandExecutor migrationCommandExecutor,
        IRelationalConnection connection,
        ISqlGenerationHelper sqlGenerationHelper,
        ICurrentDbContext currentContext,
        IModelRuntimeInitializer modelRuntimeInitializer,
        IDiagnosticsLogger<DbLoggerCategory.Migrations> logger,
        IRelationalCommandDiagnosticsLogger commandLogger,
        IDatabaseProvider databaseProvider,
        IMigrationsModelDiffer migrationsModelDiffer,
        IDesignTimeModel designTimeModel,
        IDbContextOptions contextOptions,
        IExecutionStrategy executionStrategy,
        IDsqlSqlTransform transform)
        : base(
            migrationsAssembly,
            historyRepository,
            databaseCreator,
            migrationsSqlGenerator,
            rawSqlCommandBuilder,
            migrationCommandExecutor,
            connection,
            sqlGenerationHelper,
            currentContext,
            modelRuntimeInitializer,
            logger,
            commandLogger,
            databaseProvider,
            migrationsModelDiffer,
            designTimeModel,
            contextOptions,
            executionStrategy)
    {
        _rawSqlCommandBuilder = rawSqlCommandBuilder;
        _transform = transform;
        _currentContext = currentContext;
        _commandLogger = commandLogger;
        _logger = logger;
    }

    protected override IReadOnlyList<MigrationCommand> GenerateUpSql(
        Migration migration,
        MigrationsSqlGenerationOptions options = MigrationsSqlGenerationOptions.Default)
        => TransformAndSuppress(base.GenerateUpSql(migration, options));

    protected override IReadOnlyList<MigrationCommand> GenerateDownSql(
        Migration migration,
        Migration? previousMigration,
        MigrationsSqlGenerationOptions options = MigrationsSqlGenerationOptions.Default)
        => TransformAndSuppress(base.GenerateDownSql(migration, previousMigration, options));

    private IReadOnlyList<MigrationCommand> TransformAndSuppress(
        IReadOnlyList<MigrationCommand> commands)
    {
        var sqlStatements = commands.Select(c => c.CommandText).ToList();
        var transformResult = _transform.TransformBatchWithDiagnostics(sqlStatements);

        foreach (var warning in transformResult.Warnings)
        {
            _logger.Logger.LogWarning(
                DsqlEventId.MigrationTransformWarning,
                "dsql-lint applied a behavior-changing rewrite: [{Rule}] {Message}{Preview}",
                warning.Rule,
                warning.Message,
                warning.StatementPreview != null ? $" | DDL: {warning.StatementPreview}" : "");
        }

        var result = new List<MigrationCommand>(commands.Count);
        for (var i = 0; i < commands.Count; i++)
        {
            var relationalCommand = _rawSqlCommandBuilder.Build(transformResult.Statements[i]);
            result.Add(new MigrationCommand(
                relationalCommand,
                _currentContext.Context,
                _commandLogger,
                transactionSuppressed: true));
        }

        return result;
    }
}