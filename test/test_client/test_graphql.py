"""Tests for GraphQL client module."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from graphql import GraphQLSchema

from open_targets_platform_mcp.client import graphql as graphql_module
from open_targets_platform_mcp.client.graphql import execute_graphql_query, fetch_graphql_schema
from open_targets_platform_mcp.model.query_result import QueryResultStatus


@pytest.fixture(autouse=True)
def reset_graphql_session():
    """Reset the global gql session between tests."""
    graphql_module._runtime_state.client = None
    graphql_module._runtime_state.session = None
    yield
    graphql_module._runtime_state.client = None
    graphql_module._runtime_state.session = None


def _make_mock_session(return_value=None, side_effect=None):
    """Return a mock AsyncClientSession with execute pre-configured."""
    session = AsyncMock()
    if side_effect is not None:
        session.execute = AsyncMock(side_effect=side_effect)
    else:
        session.execute = AsyncMock(return_value=return_value)
    return session


# ============================================================================
# execute_graphql_query Tests - Unit Tests with Mocks
# ============================================================================


class TestExecuteGraphQLQuery:
    """Tests for execute_graphql_query function."""

    @pytest.mark.asyncio
    async def test_execute_query_success(self, sample_query_string, sample_graphql_response):
        """Test successful query execution."""
        mock_session = _make_mock_session(return_value=sample_graphql_response)

        with patch(
            "open_targets_platform_mcp.client.graphql._get_global_graphql_session",
            return_value=mock_session,
        ):
            result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.data == sample_graphql_response
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_with_variables(
        self,
        sample_query_string,
        sample_variables,
        sample_graphql_response,
    ):
        """Test query execution with variables."""
        mock_session = _make_mock_session(return_value=sample_graphql_response)

        with patch(
            "open_targets_platform_mcp.client.graphql._get_global_graphql_session",
            return_value=mock_session,
        ):
            result = await execute_graphql_query(sample_query_string, variables=sample_variables)

        assert result.status == QueryResultStatus.SUCCESS
        mock_session.execute.assert_awaited_once()
        (request,), kwargs = mock_session.execute.call_args
        assert kwargs == {}
        assert request.variable_values == sample_variables

    @pytest.mark.asyncio
    async def test_execute_query_invalid_query_string(self):
        """Test that invalid GraphQL query strings return structured errors."""
        invalid_query = "this is not valid graphql"

        with patch("open_targets_platform_mcp.client.graphql.gql", side_effect=Exception("Parse error")):
            result = await execute_graphql_query(invalid_query)

        assert result.status == QueryResultStatus.ERROR
        assert "Parse error" in str(result.message)

    @pytest.mark.asyncio
    async def test_execute_query_execution_error(self, sample_query_string):
        """Test that query execution errors return structured errors."""
        mock_session = _make_mock_session(side_effect=Exception("Network error"))

        with patch(
            "open_targets_platform_mcp.client.graphql._get_global_graphql_session",
            return_value=mock_session,
        ):
            result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.ERROR
        assert "Network error" in str(result.message)
        mock_session.execute.assert_awaited_once()


class TestTransportConstruction:
    """Tests for transport/client construction."""

    def test_create_client_sets_content_type_header(self):
        """Test that _create_graphql_client uses the correct Content-Type header."""
        with patch("open_targets_platform_mcp.client.graphql.AIOHTTPTransport") as mock_transport:
            with patch("open_targets_platform_mcp.client.graphql.Client"):
                graphql_module._create_graphql_client()

        call_kwargs = mock_transport.call_args[1]
        assert call_kwargs["headers"] == {"Content-Type": "application/json"}


# ============================================================================
# JQ Filter Tests
# ============================================================================


class TestJQFiltering:
    """Tests for jq filter functionality."""

    @pytest.mark.asyncio
    async def test_execute_query_with_simple_jq_filter(self, sample_query_string):
        """Test query execution with simple jq filter."""
        mock_response = {
            "target": {"id": "ENSG00000141510", "approvedSymbol": "TP53", "approvedName": "tumor protein p53"},
        }
        mock_session = _make_mock_session(return_value=mock_response)

        with patch(
            "open_targets_platform_mcp.client.graphql._get_global_graphql_session",
            return_value=mock_session,
        ):
            result = await execute_graphql_query(sample_query_string, jq_filter=".target.id")

        assert result.status == QueryResultStatus.SUCCESS
        assert isinstance(result.data, list)
        assert result.data == ["ENSG00000141510"]
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_with_complex_jq_filter(self, sample_query_string):
        """Test query execution with object-building jq filter."""
        mock_response = {
            "target": {"id": "ENSG00000141510", "approvedSymbol": "TP53", "approvedName": "tumor protein p53"},
        }
        mock_session = _make_mock_session(return_value=mock_response)

        with patch(
            "open_targets_platform_mcp.client.graphql._get_global_graphql_session",
            return_value=mock_session,
        ):
            result = await execute_graphql_query(
                sample_query_string,
                jq_filter=".target | {id, symbol: .approvedSymbol}",
            )

        assert result.status == QueryResultStatus.SUCCESS
        assert isinstance(result.data, list)
        assert len(result.data) == 1
        assert isinstance(result.data[0], dict)
        assert "id" in result.data[0]
        assert "symbol" in result.data[0]
        assert result.data[0]["id"] == "ENSG00000141510"
        assert result.data[0]["symbol"] == "TP53"
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_with_array_jq_filter(self, sample_query_string):
        """Test query execution with jq filter that returns multiple results."""
        mock_response = {
            "targets": [
                {"id": "ENSG00000141510", "approvedSymbol": "TP53"},
                {"id": "ENSG00000012048", "approvedSymbol": "BRCA1"},
            ],
        }
        mock_session = _make_mock_session(return_value=mock_response)

        with patch(
            "open_targets_platform_mcp.client.graphql._get_global_graphql_session",
            return_value=mock_session,
        ):
            result = await execute_graphql_query(sample_query_string, jq_filter=".targets[] | .approvedSymbol")

        assert result.status == QueryResultStatus.SUCCESS
        assert isinstance(result.data, list)
        assert result.data == ["TP53", "BRCA1"]
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_jq_filter_error_handling(self, sample_query_string):
        """Test that jq filter runtime errors are handled gracefully."""
        mock_response = {"target": {"id": "ENSG00000141510"}}
        mock_session = _make_mock_session(return_value=mock_response)

        with (
            patch(
                "open_targets_platform_mcp.client.graphql._get_global_graphql_session",
                return_value=mock_session,
            ),
            patch("open_targets_platform_mcp.client.graphql.jq.compile") as mock_jq_compile,
        ):
            mock_compiled_filter = Mock()
            mock_compiled_filter.input_value.return_value.all.side_effect = Exception("jq execution error")
            mock_jq_compile.return_value = mock_compiled_filter

            result = await execute_graphql_query(sample_query_string, jq_filter=".invalid_filter")

        assert result.status == QueryResultStatus.WARNING
        assert result.data == mock_response
        assert "jq filter failed" in str(result.message)
        assert "// empty" in str(result.message)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_jq_compilation_error(self, sample_query_string):
        """Test that jq compilation errors return structured errors."""
        # Mock jq.compile to raise an error during compilation
        with patch("open_targets_platform_mcp.client.graphql.jq.compile") as mock_jq:
            mock_jq.side_effect = Exception("jq compilation error")

            result = await execute_graphql_query(sample_query_string, jq_filter=".invalid_filter")

        assert result.status == QueryResultStatus.ERROR
        assert "jq compilation error" in str(result.message)

    @pytest.mark.asyncio
    async def test_execute_query_no_jq_filter(self, sample_query_string, sample_graphql_response):
        """Test query execution without jq filter returns full response."""
        mock_session = _make_mock_session(return_value=sample_graphql_response)

        with patch(
            "open_targets_platform_mcp.client.graphql._get_global_graphql_session",
            return_value=mock_session,
        ):
            result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.data == sample_graphql_response
        mock_session.execute.assert_awaited_once()


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestGraphQLIntegration:
    """Integration tests with real API calls."""

    @pytest.mark.asyncio
    async def test_real_query_execution(self):
        """Test real query execution against Open Targets Platform API."""
        query = """
        query {
            target(ensemblId: "ENSG00000141510") {
                id
                approvedSymbol
            }
        }
        """

        result = await execute_graphql_query(query)

        assert result.status == QueryResultStatus.SUCCESS
        assert "target" in result.data
        assert result.data["target"]["id"] == "ENSG00000141510"
        assert result.data["target"]["approvedSymbol"] == "TP53"

    @pytest.mark.asyncio
    async def test_real_query_with_variables(self):
        """Test real query with variables."""
        query = """
        query GetTarget($ensemblId: String!) {
            target(ensemblId: $ensemblId) {
                id
                approvedSymbol
            }
        }
        """
        variables = {"ensemblId": "ENSG00000012048"}

        result = await execute_graphql_query(query, variables=variables)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.data["target"]["id"] == "ENSG00000012048"
        assert result.data["target"]["approvedSymbol"] == "BRCA1"

    @pytest.mark.asyncio
    async def test_real_query_with_jq_filter(self):
        """Test real query with jq filter."""
        query = """
        query {
            target(ensemblId: "ENSG00000141510") {
                id
                approvedSymbol
                approvedName
            }
        }
        """

        result = await execute_graphql_query(query, jq_filter=".target.approvedSymbol")

        assert result.status == QueryResultStatus.SUCCESS
        # jq filter returns a list (even for single results)
        assert isinstance(result.data, list)
        assert result.data == ["TP53"]

    @pytest.mark.asyncio
    async def test_real_invalid_query(self):
        """Test that invalid query returns error result."""
        invalid_query = """
        query {
            nonexistentField {
                id
            }
        }
        """

        result = await execute_graphql_query(invalid_query)
        assert result.status == QueryResultStatus.ERROR


# ============================================================================
# fetch_graphql_schema Tests
# ============================================================================


class TestFetchGraphQLSchema:
    """Tests for fetch_graphql_schema function."""

    @pytest.mark.asyncio
    async def test_fetch_graphql_schema_success(self):
        """Test successful schema fetching."""
        mock_schema = Mock(spec=GraphQLSchema)
        mock_client_instance = AsyncMock()
        mock_client_instance.schema = mock_schema
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("open_targets_platform_mcp.client.graphql.AIOHTTPTransport"),
            patch(
                "open_targets_platform_mcp.client.graphql.Client",
                return_value=mock_client_instance,
            ) as mock_client,
        ):
            result = await fetch_graphql_schema()

        assert result == mock_schema
        assert mock_client.call_args[1]["fetch_schema_from_transport"] is True
        mock_client_instance.__aenter__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_graphql_schema_no_schema(self):
        """Test that ValueError is raised when schema is not fetched."""
        mock_client_instance = AsyncMock()
        mock_client_instance.schema = None
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("open_targets_platform_mcp.client.graphql.AIOHTTPTransport"),
            patch(
                "open_targets_platform_mcp.client.graphql.Client",
                return_value=mock_client_instance,
            ),
            pytest.raises(ValueError, match="Failed to fetch schema"),
        ):
            await fetch_graphql_schema()
