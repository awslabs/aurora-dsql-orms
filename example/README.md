# Example Application

A simple pet clinic example demonstrating Tortoise ORM with Aurora DSQL.

## ⚠️ Important

Running this code may result in charges to your AWS account.

## Prerequisites

- An Aurora DSQL cluster
- Valid AWS credentials configured

## Setup

1. Copy the environment file and configure your cluster endpoint:

```bash
cp .env.example .env
# Edit .env with your cluster endpoint
```

2. Install dependencies from the project root:

```bash
uv sync
```

## Running

From the project root:

```bash
uv run example
```

This will:
1. Connect to your DSQL cluster
2. Create the schema (Owner, Pet, Vet, Specialty tables)
3. Insert sample data
4. Run example queries demonstrating relationships and filtering
