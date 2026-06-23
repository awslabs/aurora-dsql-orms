// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

[CollectionDefinition("DsqlTests")]
public class DsqlTestCollection : ICollectionFixture<DsqlTestFixture>, ICollectionFixture<DsqlDiTestFixture>
{
}