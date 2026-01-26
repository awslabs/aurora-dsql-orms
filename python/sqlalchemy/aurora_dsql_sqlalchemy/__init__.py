# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Aurora DSQL dialect for SQLAlchemy."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine


def create_dsql_engine(
    host: str,
    user: str,
    driver: str = "psycopg",
    dbname: str = "postgres",
    sslmode: str = "verify-full",
    sslrootcert: str = "system",
    application_name: str = "sqlalchemy",
    pool_size: int = 5,
    max_overflow: int = 10,
    connect_args: dict[str, Any] | None = None,
    **engine_kwargs: Any,
) -> Engine:
    """
    Create a SQLAlchemy engine configured for Aurora DSQL.

    This helper function simplifies engine creation by handling the connector
    setup and IAM authentication automatically.

    Args:
        host: The Aurora DSQL cluster endpoint or cluster ID.
        user: The database user (e.g., "admin").
        driver: The PostgreSQL driver to use ("psycopg" or "psycopg2").
            Defaults to "psycopg".
        dbname: The database name. Defaults to "postgres".
        sslmode: SSL mode for the connection. Defaults to "verify-full".
        sslrootcert: Path to the SSL root certificate, or "system" to use the
            system CA store. Defaults to "system".
        application_name: Application name for connection tracking.
            Defaults to "sqlalchemy".
        pool_size: The number of connections to keep in the pool.
            Defaults to 5.
        max_overflow: The number of connections to allow beyond pool_size.
            Defaults to 10.
        connect_args: Additional arguments passed to the Aurora DSQL connector
            (e.g., region, profile, token_duration_secs, custom_credentials_provider).
        **engine_kwargs: Additional keyword arguments passed to create_engine().

    Returns:
        A SQLAlchemy Engine configured for Aurora DSQL.

    Example:
        >>> from aurora_dsql_sqlalchemy import create_dsql_engine
        >>> engine = create_dsql_engine(
        ...     host="your-cluster.dsql.us-east-1.on.aws",
        ...     user="admin",
        ...     driver="psycopg",
        ...     connect_args={"profile": "my-profile"},
        ... )
    """
    conn_params = {
        "host": host,
        "user": user,
        "dbname": dbname,
        "sslmode": sslmode,
        "sslrootcert": sslrootcert,
        "application_name": application_name,
        **(connect_args or {}),
    }

    creator: Callable[[], Any]

    if driver == "psycopg":
        import aurora_dsql_psycopg as dsql_connector
        from psycopg import pq

        # Use direct SSL negotiation if supported (libpq >= 17)
        if pq.version() >= 170000:
            conn_params["sslnegotiation"] = "direct"

        def psycopg_creator():
            return dsql_connector.DSQLConnection.connect(**conn_params)

        creator = psycopg_creator
    elif driver == "psycopg2":
        import aurora_dsql_psycopg2 as dsql_connector
        import psycopg2.extensions

        # Use direct SSL negotiation if supported (libpq >= 17)
        if psycopg2.extensions.libpq_version() >= 170000:
            conn_params["sslnegotiation"] = "direct"

        def psycopg2_creator():
            return dsql_connector.connect(**conn_params)

        creator = psycopg2_creator
    else:
        raise ValueError(f"Unsupported driver: {driver}. Use 'psycopg' or 'psycopg2'.")

    url = URL.create(
        f"auroradsql+{driver}",
        username=user,
        host=host,
        database=dbname,
    )

    return create_engine(
        url,
        creator=creator,
        pool_size=pool_size,
        max_overflow=max_overflow,
        **engine_kwargs,
    )


__all__ = ["create_dsql_engine"]
