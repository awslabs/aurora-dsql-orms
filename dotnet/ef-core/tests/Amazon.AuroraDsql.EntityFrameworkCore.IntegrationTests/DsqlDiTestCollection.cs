namespace Amazon.AuroraDsql.EntityFrameworkCore.IntegrationTests;

/// <summary>
/// Test collection for DI-based pattern tests.
/// </summary>
[CollectionDefinition(nameof(DsqlDiTestCollection))]
public class DsqlDiTestCollection : ICollectionFixture<DsqlDiTestFixture>
{
}
