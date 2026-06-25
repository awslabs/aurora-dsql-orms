// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

using System.Collections.Generic;

namespace Amazon.AuroraDsql.EntityFrameworkCore.Infrastructure;

internal sealed record TransformResult(IReadOnlyList<string> Statements, IReadOnlyList<LintDiagnostic> Warnings);

internal interface IDsqlSqlTransform
{
    TransformResult TransformBatchWithDiagnostics(IReadOnlyList<string> statements);
}