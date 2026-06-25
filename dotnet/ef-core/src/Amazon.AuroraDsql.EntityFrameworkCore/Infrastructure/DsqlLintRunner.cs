// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json;

namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

internal sealed record LintDiagnostic(string Rule, string Message, string? StatementPreview, int? Line);

internal sealed record LintResult(string FixedSql, IReadOnlyList<LintDiagnostic> Warnings);

/// <summary>
/// Shells out to the dsql-lint CLI to transform SQL for Aurora DSQL compatibility.
/// </summary>
internal sealed class DsqlLintRunner
{
    private const int SupportedSchemaVersion = 1;
    private readonly string _executablePath;

    public DsqlLintRunner(string? executablePath = null)
    {
        _executablePath = executablePath ?? ResolveDsqlLint();
    }

    public string FixSql(string sql) => FixSqlWithDiagnostics(sql).FixedSql;

    public LintResult FixSqlWithDiagnostics(string sql)
    {
        ArgumentNullException.ThrowIfNull(sql);

        var psi = new ProcessStartInfo(_executablePath, "--fix --format json -")
        {
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        Process process;
        try
        {
            process = Process.Start(psi)
                ?? throw new DsqlLintException($"Failed to start '{_executablePath}'.");
        }
        catch (System.ComponentModel.Win32Exception ex)
        {
            throw new DsqlLintException(
                $"Could not find '{_executablePath}'. Ensure Amazon.AuroraDsql.Lint.Runtime is referenced " +
                "or dsql-lint is available on PATH.", ex);
        }

        using (process)
        {
            // Write stdin on a background thread to prevent pipe-buffer deadlocks when payload > 64KB.
            var stdinTask = Task.Run(() =>
            {
                process.StandardInput.Write(sql);
                process.StandardInput.Close();
            });

            var stderrTask = process.StandardError.ReadToEndAsync();
            var stdout = process.StandardOutput.ReadToEnd();
            stdinTask.GetAwaiter().GetResult();
            var stderr = stderrTask.GetAwaiter().GetResult();
            process.WaitForExit();

            // Exit 1 = unfixable errors remain — SQL is still DSQL-incompatible
            if (process.ExitCode == 1)
            {
                var diagnostics = ExtractUnfixableDiagnostics(stdout);
                throw new DsqlLintException(
                    $"dsql-lint reported unfixable DSQL-incompatible SQL. " +
                    $"Fix manually before applying migration.{diagnostics}");
            }

            // Exit 0 = no diagnostics, 3 = fixes applied with behavior-changing warnings
            if (process.ExitCode != 0 && process.ExitCode != 3)
            {
                throw new DsqlLintException(
                    $"dsql-lint exited with code {process.ExitCode}. stderr: {stderr}");
            }

            var fixedSql = ParseFixedSql(stdout, sql);
            var warnings = process.ExitCode == 3
                ? ExtractWarningDiagnostics(stdout)
                : Array.Empty<LintDiagnostic>();

            return new LintResult(fixedSql, warnings);
        }
    }

    private static string ResolveDsqlLint()
    {
        // Tier 1: explicit env override (useful for tests, CI)
        var envPath = Environment.GetEnvironmentVariable("DSQL_LINT_PATH");
        if (!string.IsNullOrEmpty(envPath) && File.Exists(envPath))
            return envPath;

        var binaryName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
            ? "dsql-lint.exe" : "dsql-lint";

        // Tier 2a: published output (binary copied to root)
        var published = Path.Combine(AppContext.BaseDirectory, binaryName);
        if (File.Exists(published))
            return published;

        // Tier 2b: non-published output (runtimes/{rid}/native/)
        var rid = RuntimeInformation.RuntimeIdentifier;
        var ridPath = Path.Combine(AppContext.BaseDirectory, "runtimes", rid, "native", binaryName);
        if (File.Exists(ridPath))
            return ridPath;

        // Tier 3: PATH fallback
        return "dsql-lint";
    }

    private static string ParseFixedSql(string json, string originalSql)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;

        ValidateSchemaVersion(root);

        if (!root.TryGetProperty("files", out var files) || files.GetArrayLength() == 0)
        {
            return originalSql;
        }

        var firstFile = files[0];
        if (firstFile.TryGetProperty("fixed_sql", out var fixedSql)
            && fixedSql.ValueKind == JsonValueKind.String)
        {
            return fixedSql.GetString() ?? originalSql;
        }

        return originalSql;
    }

    private static void ValidateSchemaVersion(JsonElement root)
    {
        if (!root.TryGetProperty("schema_version", out var version)
            || !version.TryGetInt32(out var v))
        {
            throw new DsqlLintException(
                "dsql-lint output missing or invalid 'schema_version' field. " +
                "The bundled dsql-lint binary may be incompatible — update Amazon.AuroraDsql.Lint.Runtime.");
        }

        if (v != SupportedSchemaVersion)
        {
            throw new DsqlLintException(
                $"Unsupported dsql-lint schema version {v} (expected {SupportedSchemaVersion}). " +
                "Update Amazon.AuroraDsql.EntityFrameworkCore to a compatible version.");
        }
    }

    private static string ExtractUnfixableDiagnostics(string json)
    {
        var diags = ParseDiagnostics(json, IsUnfixable);
        if (diags.Count == 0)
            return string.Empty;

        var sb = new System.Text.StringBuilder();
        foreach (var d in diags)
        {
            sb.Append($"\n  [line {d.Line?.ToString() ?? "?"}] [{d.Rule}] {d.Message}");
            if (d.StatementPreview != null)
                sb.Append($"\n    DDL: {d.StatementPreview}");
        }
        return sb.ToString();
    }

    private static IReadOnlyList<LintDiagnostic> ExtractWarningDiagnostics(string json)
        => ParseDiagnostics(json, IsFixedWithWarning);

    private static IReadOnlyList<LintDiagnostic> ParseDiagnostics(string json, Func<JsonElement, bool> predicate)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            if (!root.TryGetProperty("files", out var files) || files.GetArrayLength() == 0)
                return Array.Empty<LintDiagnostic>();

            var results = new List<LintDiagnostic>();
            foreach (var file in files.EnumerateArray())
            {
                if (!file.TryGetProperty("diagnostics", out var diags))
                    continue;
                foreach (var diag in diags.EnumerateArray())
                {
                    if (!predicate(diag))
                        continue;

                    var rule = diag.TryGetProperty("rule", out var r) ? r.GetString() ?? "unknown" : "unknown";
                    var message = diag.TryGetProperty("message", out var m) ? m.GetString() ?? "" : "";
                    var line = diag.TryGetProperty("line", out var l) && l.TryGetInt32(out var ln) ? ln : (int?)null;
                    var preview = diag.TryGetProperty("statement_preview", out var sp) ? sp.GetString() : null;

                    results.Add(new LintDiagnostic(rule, message, preview, line));
                }
            }
            return results;
        }
        catch (JsonException)
        {
            return Array.Empty<LintDiagnostic>();
        }
    }

    private static bool IsUnfixable(JsonElement diag)
    {
        if (diag.TryGetProperty("fix_result", out var fixResult)
            && fixResult.TryGetProperty("status", out var status))
        {
            return status.GetString() == "unfixable";
        }
        // If no fix_result, treat as unfixable (defensive)
        return true;
    }

    private static bool IsFixedWithWarning(JsonElement diag)
    {
        return diag.TryGetProperty("fix_result", out var fixResult)
               && fixResult.TryGetProperty("status", out var status)
               && status.GetString() == "fixed_with_warning";
    }
}

/// <summary>
/// Thrown when dsql-lint cannot be found or returns an error.
/// </summary>
internal sealed class DsqlLintException : Exception
{
    public DsqlLintException(string message) : base(message) { }
    public DsqlLintException(string message, Exception inner) : base(message, inner) { }
}