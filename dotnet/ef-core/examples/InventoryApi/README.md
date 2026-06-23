# Inventory API — Aurora DSQL EF Core Example

Minimal API demonstrating EF Core CRUD, OCC retry, batch operations, and
navigation properties against Aurora DSQL. The adapter handles IAM
authentication, command suppression, and transaction management transparently.

## Prerequisites

- .NET 8.0 SDK
- Aurora DSQL cluster
- AWS credentials configured (env vars, profile, or IAM role)

## Run

```bash
export CLUSTER_ENDPOINT="your-cluster.dsql.us-east-1.on.aws"
dotnet run --project ef-core/examples/InventoryApi/
```

## Run Integration Tests

```bash
export CLUSTER_ENDPOINT="your-cluster.dsql.us-east-1.on.aws"
dotnet test ef-core/examples/InventoryApi.IntegrationTests/
```

## Endpoints

```bash
# Create products (batch insert)
curl -X POST http://localhost:5000/products \
  -H "Content-Type: application/json" \
  -d '[{"name": "Laptop", "price": 999.99, "stock": 50},
       {"name": "Mouse", "price": 29.99, "stock": 200}]'

# List products (filtering + pagination)
curl "http://localhost:5000/products?name=Lap&page=1&pageSize=5"

# Get product
curl http://localhost:5000/products/<id>

# Place order (transaction with stock check)
curl -X POST http://localhost:5000/orders \
  -H "Content-Type: application/json" \
  -d '{"items": [{"productId": "<id>", "quantity": 2}]}'

# Get order with items (Include/ThenInclude navigation)
curl http://localhost:5000/orders/<id>
```

## What This Shows

| Feature | Where |
|---------|-------|
| DI setup (`AddDsqlDataSource` + `UseDsql`) | Program.cs |
| Standard EF Core CRUD | POST/GET /products |
| LINQ queries (filter, sort, paginate) | GET /products |
| Transactions | POST /orders |
| OCC retry (`ExecuteInTransactionAsync`) | POST /orders |
| Navigation properties (`Include`) | GET /orders/{id} |
| Batch operations | POST /products (array) |
| UUID primary keys | All entities |
| Schema setup without migrations | Program.cs startup |
