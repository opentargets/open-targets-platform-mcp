"""Tests that api_endpoint, api_call_timeout, and http_base_url settings
are correctly propagated to the GraphQL transport.
"""

from __future__ import annotations

import pytest

from open_targets_platform_mcp.client.graphql import _create_graphql_client
from open_targets_platform_mcp.settings import settings


@pytest.fixture(autouse=True)
def reset_settings():
    original_endpoint = settings.api_endpoint
    original_timeout = settings.api_call_timeout
    original_base_url = settings.http_base_url
    yield
    settings.api_endpoint = original_endpoint
    settings.api_call_timeout = original_timeout
    settings.http_base_url = original_base_url


class TestApiEndpoint:
    def test_default_endpoint_is_open_targets(self):
        client = _create_graphql_client()
        assert "opentargets.org" in client.transport.url

    def test_custom_endpoint_is_used(self):
        settings.api_endpoint = "https://example.com/graphql"
        client = _create_graphql_client()
        assert "example.com/graphql" in client.transport.url


class TestApiCallTimeout:
    def test_default_timeout_is_30(self):
        client = _create_graphql_client()
        assert client.transport.timeout == 30

    def test_custom_timeout_is_used(self):
        settings.api_call_timeout = 60
        client = _create_graphql_client()
        assert client.transport.timeout == 60


class TestHttpBaseUrl:
    def test_no_base_url_omits_parenthetical_from_user_agent(self):
        settings.http_base_url = None
        client = _create_graphql_client()
        assert "(" not in client.transport.headers["User-Agent"]

    def test_base_url_is_appended_to_user_agent(self):
        settings.http_base_url = "https://myapp.example.com"
        client = _create_graphql_client()
        assert " (https://myapp.example.com/)" in client.transport.headers["User-Agent"]
