# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

from botocore.credentials import CredentialProvider, Credentials
from botocore.session import get_session
from sqlalchemy import text
from sqlalchemy.testing import fixtures

from aurora_dsql_sqlalchemy import create_dsql_engine

from .conftest import CLUSTER_ENDPOINT, CLUSTER_ID, CLUSTER_USER, DRIVER, REGION

assert CLUSTER_ENDPOINT is not None


class TrackingCredentialsProvider(CredentialProvider):
    METHOD = "custom-tracking"

    def __init__(self):
        super().__init__()
        self.load_called = False

    def load(self) -> Credentials:  # type: ignore[override]
        self.load_called = True
        session = get_session()
        creds = session.get_credentials()
        return Credentials(creds.access_key, creds.secret_key, creds.token)


def _verify_connection(engine):
    """Verify the engine can connect and execute a simple query."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


class TestConnectorIntegration(fixtures.TestBase):
    """Integration tests verifying connector parameters work correctly."""

    def test_profile_used_for_connection(self):
        """Verify that profile parameter is passed to boto3 Session."""
        with patch("dsql_core.token_manager.boto3.Session") as mock_session:
            mock_client = mock_session.return_value.client.return_value
            mock_client.generate_db_connect_admin_auth_token.return_value = "mock-token"
            engine = create_dsql_engine(
                host=CLUSTER_ENDPOINT,
                user=CLUSTER_USER,
                driver=DRIVER,
                connect_args={"profile": "test-profile"},
            )
            try:
                engine.connect()
            except Exception:
                pass  # Connection will fail with mock token
            mock_session.assert_called_with(profile_name="test-profile")

    def test_cluster_id_with_region(self):
        """Verify that cluster ID with region parameter works."""
        engine = create_dsql_engine(
            host=CLUSTER_ID,
            user=CLUSTER_USER,
            driver=DRIVER,
            connect_args={"region": REGION},
        )
        _verify_connection(engine)

    def test_token_duration_secs(self):
        """Verify that token_duration_secs parameter works."""
        engine = create_dsql_engine(
            host=CLUSTER_ENDPOINT,
            user=CLUSTER_USER,
            driver=DRIVER,
            connect_args={"token_duration_secs": 900},
        )
        _verify_connection(engine)

    def test_custom_credentials_provider(self):
        """Verify that custom_credentials_provider parameter works."""
        provider = TrackingCredentialsProvider()
        engine = create_dsql_engine(
            host=CLUSTER_ENDPOINT,
            user=CLUSTER_USER,
            driver=DRIVER,
            connect_args={"custom_credentials_provider": provider},
        )
        _verify_connection(engine)
        assert provider.load_called
