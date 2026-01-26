# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import re
import urllib.parse

from tortoise.backends.base.config_generator import DB_LOOKUP


def _str_to_bool(value):
    """Convert string to bool. Needed because bool('false') returns True."""
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


# Parameters specific to the DSQL python connector, not pool or specific driver.
DSQL_CONNECTOR_PARAMS = {
    "region",
    "custom_credentials_provider",
    "profile",
    "token_duration_secs",
}

DSQL_CONNECTOR_CASTS = {
    "token_duration_secs": int,
}

_COMMON_POOL_CASTS = {
    "max_size": int,
    "min_size": int,
    "timeout": float,
}

_COMMON_CONNECTION_CASTS = {
    "port": int,
}

ASYNCPG_CASTS = {
    **_COMMON_POOL_CASTS,
    **_COMMON_CONNECTION_CASTS,
    # pool
    "max_inactive_connection_lifetime": float,
    "max_queries": int,
    # connection
    "command_timeout": float,
    "direct_tls": _str_to_bool,
    "max_cacheable_statement_size": int,
    "max_cached_statement_lifetime": float,
    "statement_cache_size": int,
}

PSYCOPG_CASTS = {
    **_COMMON_POOL_CASTS,
    **_COMMON_CONNECTION_CASTS,
    # pool
    "close_returns": _str_to_bool,
    "max_idle": float,
    "max_lifetime": float,
    "max_waiting": int,
    "num_workers": int,
    "open": _str_to_bool,
    "reconnect_timeout": float,
    # connection
    "autocommit": _str_to_bool,
    "connect_timeout": int,
    "prepare_threshold": int,
}

# This expression is used to tokenize a series of SQL statements, so they can be
# split for individual execution. We can't simply split on semicolons, as they
# may be within a quoted string or comment.
_TOKEN_RE = re.compile(
    r"""
    ;                                            # semicolon
    |'[^']*(?:''[^']*)*'                         # single-quoted string
    |"[^"]*(?:""[^"]*)*"                         # double-quoted identifier
    |\$\$.*?\$\$                                 # dollar-quoted string (no tag)
    |(\$(?P<tag>[a-zA-Z_]\w*)\$.*?\$(?P=tag)\$)  # dollar-quoted string (with tag)
    |\$                                          # lone dollar sign
    |-(?!-)                                      # lone dash (not start of --)
    |/(?!\*)                                     # lone slash (not start of /*)
    |--[^\r\n]*                                  # single-line comment
    |/\*.*?\*/                                   # multi-line comment
    |[^;'"$/-]+                                  # everything else
    """,
    re.VERBOSE | re.DOTALL,
)


def split_sql(query: str) -> list[str]:
    """Split SQL on semicolons, preserving semicolons inside quoted strings."""
    result = []
    current = []
    for match in _TOKEN_RE.finditer(query):
        token = match.group()
        if token == ";":
            statement = "".join(current).strip()
            if statement:
                result.append(statement)
            current = []
        else:
            current.append(token)

    # Add remaining as a statement, semicolon or not.
    statement = "".join(current).strip()
    if statement:
        result.append(statement)

    return result


def register_backend(module_name: str, casts: dict) -> str:
    """Register DSQL backend with Tortoise ORM. Returns the scheme."""
    scheme = "dsql+" + module_name.rsplit(".", 1)[-1]
    if scheme not in DB_LOOKUP:
        urllib.parse.uses_netloc.append(scheme)
        DB_LOOKUP[scheme] = {
            "engine": module_name,
            "vmap": {
                "path": "database",
                "hostname": "host",
                "port": "port",
                "username": "user",
                "password": "password",
            },
            "defaults": {},
            "cast": {**DSQL_CONNECTOR_CASTS, **casts},
        }
    return scheme
