# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.testing import fixtures

from aurora_dsql_sqlalchemy import create_dsql_engine

from .conftest import DRIVER

LIBPQ_16 = 160000
LIBPQ_17 = 170000
DEFAULT_LIBPQ_VERSION = LIBPQ_16


@pytest.fixture
def mock_driver():
    """Mock driver dependencies for testing based on configured DRIVER."""
    if DRIVER == "psycopg":
        with (
            patch("aurora_dsql_sqlalchemy.create_engine") as mock_create_engine,
            patch("aurora_dsql_psycopg.DSQLConnection") as mock_conn,
            patch("psycopg.pq") as mock_pq,
        ):
            mock_pq.version.return_value = DEFAULT_LIBPQ_VERSION
            mock_create_engine.return_value = MagicMock()
            yield {
                "create_engine": mock_create_engine,
                "conn": mock_conn,
                "pq": mock_pq,
            }
    else:
        with (
            patch("aurora_dsql_sqlalchemy.create_engine") as mock_create_engine,
            patch("aurora_dsql_psycopg2.connect") as mock_connect,
            patch("psycopg2.extensions") as mock_ext,
        ):
            mock_ext.libpq_version.return_value = DEFAULT_LIBPQ_VERSION
            mock_create_engine.return_value = MagicMock()
            yield {
                "create_engine": mock_create_engine,
                "connect": mock_connect,
                "ext": mock_ext,
            }


class TestCreateDsqlEngine(fixtures.TestBase):
    """Unit tests for create_dsql_engine function."""

    @pytest.mark.parametrize(
        "param,expected",
        [
            ("pool_size", 5),
            ("max_overflow", 10),
        ],
    )
    def test_default_engine_params(self, mock_driver, param, expected):
        """Verify default engine parameters."""
        create_dsql_engine(
            host="test.dsql.us-east-1.on.aws", user="admin", driver=DRIVER
        )
        assert mock_driver["create_engine"].call_args.kwargs[param] == expected

    def test_default_driver_is_psycopg(self, mock_driver):
        """Verify default driver is psycopg."""
        if DRIVER != "psycopg":
            pytest.skip("psycopg driver not configured")
        create_dsql_engine(host="test.dsql.us-east-1.on.aws", user="admin")
        url = mock_driver["create_engine"].call_args.args[0]
        assert "psycopg" in str(url)
        assert "psycopg2" not in str(url)

    def test_default_dbname(self, mock_driver):
        """Verify default dbname is postgres."""
        create_dsql_engine(
            host="test.dsql.us-east-1.on.aws", user="admin", driver=DRIVER
        )
        url = mock_driver["create_engine"].call_args.args[0]
        assert url.database == "postgres"

    def test_custom_pool_size(self, mock_driver):
        """Verify custom pool_size is passed through."""
        create_dsql_engine(
            host="test.dsql.us-east-1.on.aws", user="admin", driver=DRIVER, pool_size=20
        )
        assert mock_driver["create_engine"].call_args.kwargs["pool_size"] == 20

    def test_invalid_driver_raises(self):
        """Verify invalid driver raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported driver"):
            create_dsql_engine(
                host="test.dsql.us-east-1.on.aws", user="admin", driver="invalid"
            )

    @pytest.mark.parametrize(
        "libpq_version,expect_direct", [(LIBPQ_17, True), (LIBPQ_16, False)]
    )
    def test_sslnegotiation_based_on_libpq_version(
        self, mock_driver, libpq_version, expect_direct
    ):
        """Verify sslnegotiation is set based on libpq version."""
        if DRIVER == "psycopg":
            mock_driver["pq"].version.return_value = libpq_version
        else:
            mock_driver["ext"].libpq_version.return_value = libpq_version

        create_dsql_engine(
            host="test.dsql.us-east-1.on.aws", user="admin", driver=DRIVER
        )

        creator = mock_driver["create_engine"].call_args.kwargs["creator"]
        creator()

        if DRIVER == "psycopg":
            conn_kwargs = mock_driver["conn"].connect.call_args.kwargs
        else:
            conn_kwargs = mock_driver["connect"].call_args.kwargs

        if expect_direct:
            assert conn_kwargs.get("sslnegotiation") == "direct"
        else:
            assert "sslnegotiation" not in conn_kwargs

    def test_engine_kwargs_passed_through(self, mock_driver):
        """Verify extra engine kwargs are passed to create_engine."""
        create_dsql_engine(
            host="test.dsql.us-east-1.on.aws",
            user="admin",
            driver=DRIVER,
            echo=True,
            pool_pre_ping=True,
        )
        assert mock_driver["create_engine"].call_args.kwargs["echo"] is True
        assert mock_driver["create_engine"].call_args.kwargs["pool_pre_ping"] is True
