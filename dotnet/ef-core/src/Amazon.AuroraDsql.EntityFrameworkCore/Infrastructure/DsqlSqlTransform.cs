// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

/// <summary>
/// Combines dsql-lint fixes with idempotency rewrites so partially-applied
/// migrations are safe to re-run.
/// </summary>
internal sealed partial class DsqlSqlTransform : IDsqlSqlTransform
{
    private readonly DsqlLintRunner _runner;

    public DsqlSqlTransform(DsqlLintRunner? runner = null)
    {
        _runner = runner ?? new DsqlLintRunner();
    }

    public TransformResult TransformBatchWithDiagnostics(IReadOnlyList<string> statements)
    {
        if (statements.Count == 0)
            return new TransformResult(statements, Array.Empty<LintDiagnostic>());

        // Partition into DDL (needs lint) and non-DDL (pass-through)
        var ddlIndices = new List<int>();
        var ddlStatements = new List<string>();
        for (var i = 0; i < statements.Count; i++)
        {
            if (!string.IsNullOrWhiteSpace(statements[i]) && IsDdl(statements[i]))
            {
                ddlIndices.Add(i);
                ddlStatements.Add(statements[i].TrimEnd());
            }
        }

        if (ddlStatements.Count == 0)
            return new TransformResult(statements, Array.Empty<LintDiagnostic>());

        // Try batch: join DDL, lint once, split back
        var (batchedResults, warnings) = TryBatchLint(ddlStatements);

        // Build output preserving original order
        var result = new string[statements.Count];
        for (var i = 0; i < statements.Count; i++)
            result[i] = statements[i];

        if (batchedResults != null)
        {
            for (var i = 0; i < ddlIndices.Count; i++)
                result[ddlIndices[i]] = MakeIdempotent(batchedResults[i]);
        }
        else
        {
            // Fallback: per-statement lint. Discard batch warnings — they reference
            // line numbers from the concatenated script which was not used.
            var allWarnings = new List<LintDiagnostic>();
            for (var i = 0; i < ddlIndices.Count; i++)
            {
                var lintResult = _runner.FixSqlWithDiagnostics(ddlStatements[i]);
                result[ddlIndices[i]] = MakeIdempotent(lintResult.FixedSql);
                allWarnings.AddRange(lintResult.Warnings);
            }
            warnings = allWarnings;
        }

        return new TransformResult(result, warnings);
    }

    private (List<string>? Statements, IReadOnlyList<LintDiagnostic> Warnings) TryBatchLint(List<string> ddlStatements)
    {
        if (ddlStatements.Count == 1)
        {
            var lintResult = _runner.FixSqlWithDiagnostics(ddlStatements[0]);
            return (new List<string> { lintResult.FixedSql }, lintResult.Warnings);
        }

        // Join with semicolons and lint as a single script
        var script = string.Join(";\n", ddlStatements.Select(s => s.TrimEnd().TrimEnd(';'))) + ";\n";
        var batchResult = _runner.FixSqlWithDiagnostics(script);

        // Split back on statement boundaries
        var split = batchResult.FixedSql
            .Split(';')
            .Select(s => s.Trim())
            .Where(s => s.Length > 0)
            .Select(s => s + ";")
            .ToList();

        // If count doesn't match, fall back to per-statement
        if (split.Count != ddlStatements.Count)
            return (null, batchResult.Warnings);

        return (split, batchResult.Warnings);
    }

    [GeneratedRegex(@"^\s*(CREATE|ALTER|DROP)\b", RegexOptions.IgnoreCase)]
    private static partial Regex DdlPrefixRegex();

    private static bool IsDdl(string sql) => DdlPrefixRegex().IsMatch(sql);

    [GeneratedRegex(@"\bCREATE\s+TABLE\s+(?!IF\s+NOT\s+EXISTS\b)",
        RegexOptions.IgnoreCase)]
    private static partial Regex CreateTableRegex();

    [GeneratedRegex(@"\bCREATE\s+(UNIQUE\s+)?INDEX\s+(ASYNC\s+)?(?!IF\s+NOT\s+EXISTS\b)",
        RegexOptions.IgnoreCase)]
    private static partial Regex CreateIndexRegex();

    /// <summary>
    /// Rewrites CREATE TABLE and CREATE [UNIQUE] INDEX [ASYNC] statements to include
    /// IF NOT EXISTS, making them safe to re-run on partially-applied migrations.
    /// ALTER/DROP statements are NOT rewritten — those require manual intervention
    /// if a migration fails partway through and must be replayed.
    /// </summary>
    public static string MakeIdempotent(string sql)
    {
        var result = CreateTableRegex().Replace(sql, m =>
        {
            var trimmed = m.Value.TrimEnd();
            return trimmed + " IF NOT EXISTS ";
        });
        result = CreateIndexRegex().Replace(result, m =>
        {
            var trimmed = m.Value.TrimEnd();
            return trimmed + " IF NOT EXISTS ";
        });
        return result;
    }
}