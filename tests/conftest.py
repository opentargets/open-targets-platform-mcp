"""Pytest configuration and fixtures for otar_mcp tests."""

import pytest


@pytest.fixture
def mock_api_endpoint() -> str:
    """Mock OpenTargets API endpoint for testing."""
    return "https://api.platform.opentargets.org/api/v4/graphql"


@pytest.fixture
def sample_query_string() -> str:
    """Sample GraphQL query string for testing."""
    return """
    query testQuery {
        target(ensemblId: "ENSG00000141510") {
            id
            approvedSymbol
        }
    }
    """


@pytest.fixture
def sample_variables() -> dict:
    """Sample GraphQL query variables for testing."""
    return {"ensemblId": "ENSG00000141510"}
