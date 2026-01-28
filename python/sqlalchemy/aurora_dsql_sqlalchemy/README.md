# Aurora DSQL Dialect for SQLAlchemy - Developer instructions

## Clone the repository

```bash
git clone https://github.com/awslabs/aurora-dsql-orms.git
cd aurora-dsql-orms/python/sqlalchemy
```

## Install `uv`

Install `uv` using the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/) or via [mise](https://mise.jdx.dev/).

## Configure SSL certificates

See [SSL/TLS Configuration](../docs/SSL_CONFIGURATION.md) for instructions on configuring certificate trust.

## Install dependencies

```bash
uv sync
```

## Set up pre-commit hooks

```bash
uv run pre-commit install
```

## Configure environment variables

Copy `.env.example` to `.env` and update with your cluster details:

```bash
cp .env.example .env
```

Use `DRIVER=psycopg2` when testing against the `psycopg2` driver.

Alternatively, set the following variables to connect to your cluster:

```bash
export CLUSTER_ENDPOINT=<YOUR_CLUSTER_HOSTNAME>
export CLUSTER_USER=admin
export DRIVER=psycopg
```

## Running integration tests

```bash
uv run pytest
```
