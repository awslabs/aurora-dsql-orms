# Veterinary App Example

A sample application demonstrating Prisma with Amazon Aurora DSQL.

## Overview

This example shows:

- DSQL-compatible Prisma schema with UUID primary keys and `relationMode = "prisma"`
- DsqlPrismaClient wrapper with automatic IAM authentication
- CRUD operations for a veterinary clinic domain (owners, pets, vets, specialties)
- Integration tests

## Prerequisites

- Node.js 20.0.0 or later
- AWS credentials configured
- An Aurora DSQL cluster

## Setup

1. Install dependencies:

    ```bash
    npm install
    ```

2. Set environment variables:

    ```bash
    export CLUSTER_USER="admin"
    export CLUSTER_ENDPOINT="your-cluster.dsql.us-east-1.on.aws"
    ```

3. Build the project:

    ```bash
    npm run build
    ```

4. Apply migrations:
    ```bash
    npm run prisma:migrate-up
    ```

## Run

```bash
npm run sample
```

## Test

```bash
npm test
```

## Clean Up

```bash
npm run prisma:migrate-down
```

## Project Structure

```
├── src/
│   ├── dsql-client.ts        # Prisma client with IAM auth
│   ├── veterinary-service.ts # Business logic
│   ├── example.ts            # Demo code
│   └── index.ts              # Entry point
├── prisma/
│   ├── veterinary-schema.prisma
│   └── migrations/
└── test/
    └── dsql-client.test.ts   # Integration tests
```
