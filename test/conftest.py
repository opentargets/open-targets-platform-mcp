"""Pytest configuration and fixtures for otar_mcp tests."""

from unittest.mock import MagicMock, Mock

import pytest
from graphql import GraphQLSchema, build_schema

# ============================================================================
# Test Markers Configuration
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests (requires real API access)")


# ============================================================================
# API Endpoint Fixtures
# ============================================================================


@pytest.fixture
def mock_api_endpoint() -> str:
    """Mock Open Targets Platform API endpoint for testing."""
    return "https://api.platform.opentargets.org/api/v4/graphql"


# ============================================================================
# GraphQL Query Fixtures
# ============================================================================


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


@pytest.fixture
def sample_batch_variables() -> list[dict]:
    """Sample batch query variables for testing."""
    return [
        {"ensemblId": "ENSG00000141510"},
        {"ensemblId": "ENSG00000012048"},
        {"ensemblId": "ENSG00000139618"},
    ]


@pytest.fixture
def sample_search_query() -> str:
    """Sample search query GraphQL string."""
    return """
    query searchQuery($queryString: String!) {
        search(queryString: $queryString) {
            hits {
                id
                entity
                name
            }
        }
    }
    """


# ============================================================================
# GraphQL Response Fixtures
# ============================================================================


@pytest.fixture
def sample_graphql_response() -> dict:
    """Sample successful GraphQL response."""
    return {"target": {"id": "ENSG00000141510", "approvedSymbol": "TP53"}}


@pytest.fixture
def sample_search_response() -> dict:
    """Sample search API response."""
    return {
        "search": {
            "hits": [
                {"id": "ENSG00000012048", "entity": "target", "name": "BRCA1"},
                {"id": "EFO_0000305", "entity": "disease", "name": "breast carcinoma"},
                {"id": "CHEMBL25", "entity": "drug", "name": "Aspirin"},
            ],
        },
    }


@pytest.fixture
def sample_error_response() -> dict:
    """Sample error response from GraphQL."""
    return {"status": "error", "message": "Query execution failed"}


# ============================================================================
# GraphQL Client Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_graphql_schema() -> GraphQLSchema:
    """Mock GraphQL schema for testing."""
    schema_definition = """
    type Query {
        target(ensemblId: String!): Target
        disease(efoId: String!): Disease
        drug(chemblId: String!): Drug
        search(queryString: String!): SearchResult
    }

    type Target {
        id: String!
        approvedSymbol: String
        approvedName: String
    }

    type Disease {
        id: String!
        name: String
    }

    type Drug {
        id: String!
        name: String
    }

    type SearchResult {
        hits: [SearchHit]
    }

    type SearchHit {
        id: String!
        entity: String!
        name: String
    }
    """
    return build_schema(schema_definition)


@pytest.fixture
def rich_mock_schema() -> GraphQLSchema:
    """Comprehensive GraphQL schema for RLM testing."""
    schema_definition = """
    type Query {
        target(ensemblId: String!): Target
        disease(efoId: String!): Disease
        drug(chemblId: String!): Drug
        search(queryString: String!, page: Int = 0): SearchResult
    }

    interface Node {
        id: String!
    }

    type Target implements Node {
        id: String!
        approvedSymbol: String
        approvedName: String
        cancerBiomarkers: [CancerBiomarker]
        associatedDiseases(page: Int = 0, size: Int = 10): DiseasePaginated
        proteinAnnotations: ProteinAnnotations
    }

    type Disease implements Node {
        id: String!
        name: String!
        description: String
        therapeuticAreas: [TherapeuticArea]
        synonyms: [String]
    }

    type Drug implements Node {
        id: String!
        name: String!
        maximumClinicalTrialPhase: Int
        tradeNames: [String]
    }

    type CancerBiomarker {
        id: String!
        diseaseFromSource: String
        biomarkerName: String
    }

    type DiseasePaginated {
        count: Int!
        rows: [Disease]!
    }

    type TherapeuticArea {
        id: String!
        name: String!
    }

    type ProteinAnnotations {
        id: String!
        functions: [String]
        subcellularLocations: [String]
    }

    type SearchResult {
        total: Int!
        hits: [SearchHit]
    }

    type SearchHit {
        id: String!
        entity: String!
        name: String
        score: Float
    }

    input TargetFilter {
        symbol: String
        minAssociationScore: Float
        therapeuticArea: String
    }

    input DiseaseFilter {
        therapeuticArea: String
        minPrevalence: Float
    }

    enum EntityType {
        TARGET
        DISEASE
        DRUG
        VARIANT
        STUDY
    }

    enum ClinicalPhase {
        PHASE_0
        PHASE_1
        PHASE_2
        PHASE_3
        PHASE_4
    }

    scalar JSON
    scalar Date
    """
    return build_schema(schema_definition)


@pytest.fixture
def mock_graphql_client(sample_graphql_response, mock_graphql_schema):
    """Mock GQL Client for testing."""
    client = MagicMock()
    client.execute.return_value = sample_graphql_response
    client.schema = mock_graphql_schema
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    return client


@pytest.fixture
def clear_schema_cache():
    """Clear all schema caches before and after test."""
    from open_targets_platform_mcp.tools.schema import schema
    from open_targets_platform_mcp.tools.schema_explorer import schema_explorer

    schema._cache.clear()
    schema_explorer._explorer_cache.clear()

    yield

    schema._cache.clear()
    schema_explorer._explorer_cache.clear()


# ============================================================================
# JQ Filter Fixtures
# ============================================================================


@pytest.fixture
def simple_jq_filter() -> str:
    """Simple jq filter for testing."""
    return ".data.target"


@pytest.fixture
def complex_jq_filter() -> str:
    """Complex jq filter for testing."""
    return ".data.target | {id, symbol: .approvedSymbol}"


# ============================================================================
# Environment Variable Fixtures
# ============================================================================


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all Open Targets Platform environment variables."""
    env_vars = [
        "OTP_MCP_API_ENDPOINT",
        "OTP_MCP_SERVER_NAME",
        "OTP_MCP_HTTP_HOST",
        "OTP_MCP_HTTP_PORT",
        "OTP_MCP_API_CALL_TIMEOUT",
        "OTP_MCP_JQ_ENABLED",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def custom_env(monkeypatch):
    """Set custom environment variables for testing."""
    monkeypatch.setenv("OTP_MCP_API_ENDPOINT", "https://custom.api.test/graphql")
    monkeypatch.setenv("OTP_MCP_SERVER_NAME", "Test Server")
    monkeypatch.setenv("OTP_MCP_HTTP_HOST", "0.0.0.0")
    monkeypatch.setenv("OTP_MCP_HTTP_PORT", "9000")
    monkeypatch.setenv("OTP_MCP_API_CALL_TIMEOUT", "60")


# ============================================================================
# File System Fixtures
# ============================================================================


@pytest.fixture
def sample_gql_file_content() -> str:
    """Sample .gql file content with metadata."""
    return """# Query Name: GetTargetInfo
# Entity Type: target
# Description: Retrieve basic information about a target
# Variables: ensemblId (String!) - The ENSEMBL ID of the target
# Pagination Behavior: None - single target query

query GetTargetInfo($ensemblId: String!) {
    target(ensemblId: $ensemblId) {
        id
        approvedSymbol
        approvedName
    }
}
"""


@pytest.fixture
def sample_category_descriptors() -> dict:
    """Sample category descriptors mapping."""
    return {
        "target": "Queries related to genes and protein targets",
        "disease": "Queries for disease and phenotype information",
        "drug": "Queries for drug and molecule information",
    }


@pytest.fixture
def sample_category_query_mapper() -> dict:
    """Sample category to query mapping."""
    return {
        "target": ["GetTargetInfo", "GetTargetAssociations"],
        "disease": ["GetDiseaseInfo", "GetDiseaseAssociations"],
        "drug": ["GetDrugInfo", "GetDrugMechanisms"],
    }


# ============================================================================
# Batch Query Fixtures
# ============================================================================


@pytest.fixture
def batch_query_string() -> str:
    """GraphQL query string for batch testing."""
    return """
    query GetTarget($ensemblId: String!) {
        target(ensemblId: $ensemblId) {
            id
            approvedSymbol
        }
    }
    """


@pytest.fixture
def batch_variables_with_key() -> list[dict]:
    """Batch variables with consistent key field."""
    return [
        {"ensemblId": "ENSG00000141510", "name": "TP53"},
        {"ensemblId": "ENSG00000012048", "name": "BRCA1"},
        {"ensemblId": "ENSG00000139618", "name": "BRCA2"},
    ]


@pytest.fixture
def batch_expected_results() -> dict:
    """Expected batch query results."""
    return {
        "ENSG00000141510": {
            "status": "success",
            "data": {"target": {"id": "ENSG00000141510", "approvedSymbol": "TP53"}},
        },
        "ENSG00000012048": {
            "status": "success",
            "data": {"target": {"id": "ENSG00000012048", "approvedSymbol": "BRCA1"}},
        },
        "ENSG00000139618": {
            "status": "success",
            "data": {"target": {"id": "ENSG00000139618", "approvedSymbol": "BRCA2"}},
        },
    }
