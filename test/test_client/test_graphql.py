"""Tests for GraphQL client module."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from gql.transport.exceptions import (
    TransportConnectionFailed,
    TransportProtocolError,
    TransportQueryError,
    TransportServerError,
)
from graphql import GraphQLSchema

from open_targets_platform_mcp.client.graphql import execute_graphql_query, fetch_graphql_schema
from open_targets_platform_mcp.model.result import QueryResultStatus

# ============================================================================
# execute_graphql_query Tests - Unit Tests with Mocks
# ============================================================================


class TestExecuteGraphQLQuery:
    """Tests for execute_graphql_query function."""

    @pytest.mark.asyncio
    async def test_execute_query_success(self, sample_query_string, sample_graphql_response):
        """Test successful query execution."""
        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(return_value=sample_graphql_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance):
                result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.result == sample_graphql_response
        mock_client_instance.execute_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_with_variables(
        self,
        sample_query_string,
        sample_variables,
        sample_graphql_response,
    ):
        """Test query execution with variables."""
        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(return_value=sample_graphql_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance):
                result = await execute_graphql_query(sample_query_string, variables=sample_variables)

        assert result.status == QueryResultStatus.SUCCESS
        mock_client_instance.execute_async.assert_awaited_once_with("parsed_query", variable_values=sample_variables)

    @pytest.mark.asyncio
    async def test_execute_query_default_headers(self, sample_query_string):
        """Test that default headers are set when none provided."""
        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(return_value={})

        with patch("open_targets_platform_mcp.client.graphql.AIOHTTPTransport") as mock_transport:
            with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
                with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance):
                    await execute_graphql_query(sample_query_string)

        call_kwargs = mock_transport.call_args[1]
        assert call_kwargs["headers"] == {"Content-Type": "application/json"}

    @pytest.mark.asyncio
    async def test_execute_query_invalid_query_string(self):
        """Test that invalid GraphQL query string errors bubble up."""
        invalid_query = "this is not valid graphql"

        with patch("open_targets_platform_mcp.client.graphql.gql", side_effect=Exception("Parse error")):
            with pytest.raises(Exception, match="Parse error"):
                await execute_graphql_query(invalid_query)

    @pytest.mark.asyncio
    async def test_execute_query_execution_error(self, sample_query_string):
        """Generic (non-transport) execution errors still bubble up.

        Only `gql.transport.exceptions.Transport*` and `asyncio.TimeoutError`
        are converted to structured `QueryResult.create_error`. Anything else
        is treated as a programmer bug and surfaces as the original exception.
        """
        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(side_effect=Exception("Network error"))

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance):
                with pytest.raises(Exception, match="Network error"):
                    await execute_graphql_query(sample_query_string)

        mock_client_instance.execute_async.assert_awaited_once()


# ============================================================================
# Transport-error conversion to structured QueryResult
# ============================================================================


class TestTransportErrorConversion:
    """Verify that transport exceptions are converted to QueryResult.ERROR."""

    @pytest.mark.asyncio
    async def test_transport_query_error_returns_structured_result(
        self,
        sample_query_string,
        mock_graphql_schema,
    ):
        """`TransportQueryError` -> QueryResult.ERROR with hints from the live schema cache."""
        graphql_errors = [
            {
                "message": "Cannot query field 'symbol' on type 'Target'.",
                "locations": [{"line": 1, "column": 1}],
            },
        ]
        exc = TransportQueryError("query failed", errors=graphql_errors, data=None)

        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(side_effect=exc)

        with (
            patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"),
            patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance),
            patch(
                "open_targets_platform_mcp.client.graphql._get_cached_schema_safe",
                AsyncMock(return_value=mock_graphql_schema),
            ),
        ):
            result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.ERROR
        assert isinstance(result.message, dict)
        assert result.message["error_type"] == "graphql_query_error"
        assert result.message["errors"] == graphql_errors
        assert result.message["partial_data"] is None
        hints = result.message["hints"]
        assert len(hints) == 1
        assert hints[0]["category"] == "unknown_field"
        assert hints[0]["type"] == "Target"
        assert "approvedSymbol" in hints[0]["did_you_mean"]

    @pytest.mark.asyncio
    async def test_transport_query_error_with_cold_schema_cache(self, sample_query_string):
        """If the schema cache fails, hints still ship without `available_fields`."""
        graphql_errors = [
            {"message": "Cannot query field 'symbol' on type 'Target'."},
        ]
        exc = TransportQueryError("query failed", errors=graphql_errors)

        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(side_effect=exc)

        with (
            patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"),
            patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance),
            patch(
                "open_targets_platform_mcp.client.graphql._get_cached_schema_safe",
                AsyncMock(return_value=None),
            ),
        ):
            result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.ERROR
        hint = result.message["hints"][0]
        assert hint["category"] == "unknown_field"
        assert hint["type"] == "Target"
        assert "available_fields" not in hint

    @pytest.mark.asyncio
    async def test_transport_query_error_propagates_partial_data(
        self,
        sample_query_string,
        mock_graphql_schema,
    ):
        """`TransportQueryError.data` (partial GraphQL data) is forwarded to the caller."""
        partial = {"target": None}
        exc = TransportQueryError(
            "query failed",
            errors=[{"message": "Cannot query field 'x' on type 'Target'."}],
            data=partial,
        )

        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(side_effect=exc)

        with (
            patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"),
            patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance),
            patch(
                "open_targets_platform_mcp.client.graphql._get_cached_schema_safe",
                AsyncMock(return_value=mock_graphql_schema),
            ),
        ):
            result = await execute_graphql_query(sample_query_string)

        assert result.message["partial_data"] == partial

    @pytest.mark.asyncio
    async def test_transport_server_error(self, sample_query_string):
        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(
            side_effect=TransportServerError("HTTP 503"),
        )

        with (
            patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"),
            patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance),
        ):
            result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.ERROR
        assert result.message["error_type"] == "server_error"
        assert "503" in result.message["detail"]

    @pytest.mark.asyncio
    async def test_transport_protocol_error(self, sample_query_string):
        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(
            side_effect=TransportProtocolError("malformed response"),
        )

        with (
            patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"),
            patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance),
        ):
            result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.ERROR
        assert result.message["error_type"] == "protocol_error"

    @pytest.mark.asyncio
    async def test_transport_connection_failed(self, sample_query_string):
        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(
            side_effect=TransportConnectionFailed("dns failure"),
        )

        with (
            patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"),
            patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance),
        ):
            result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.ERROR
        assert result.message["error_type"] == "connection_error"

    @pytest.mark.asyncio
    async def test_asyncio_timeout(self, sample_query_string):
        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(
            side_effect=asyncio.TimeoutError("slow"),
        )

        with (
            patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"),
            patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance),
        ):
            result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.ERROR
        assert result.message["error_type"] == "timeout"


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

        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(return_value=mock_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance):
                result = await execute_graphql_query(sample_query_string, jq_filter=".target.id")

        # jq filter returns a list (even for single results)
        assert result.status == QueryResultStatus.SUCCESS
        assert isinstance(result.result, list)
        assert result.result == ["ENSG00000141510"]
        mock_client_instance.execute_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_with_complex_jq_filter(self, sample_query_string):
        """Test query execution with object-building jq filter."""
        mock_response = {
            "target": {"id": "ENSG00000141510", "approvedSymbol": "TP53", "approvedName": "tumor protein p53"},
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(return_value=mock_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance):
                result = await execute_graphql_query(
                    sample_query_string,
                    jq_filter=".target | {id, symbol: .approvedSymbol}",
                )

        # jq filter returns a list (even for single results)
        assert result.status == QueryResultStatus.SUCCESS
        assert isinstance(result.result, list)
        assert len(result.result) == 1
        assert isinstance(result.result[0], dict)
        assert "id" in result.result[0]
        assert "symbol" in result.result[0]
        assert result.result[0]["id"] == "ENSG00000141510"
        assert result.result[0]["symbol"] == "TP53"
        mock_client_instance.execute_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_with_array_jq_filter(self, sample_query_string):
        """Test query execution with jq filter that returns multiple results."""
        mock_response = {
            "targets": [
                {"id": "ENSG00000141510", "approvedSymbol": "TP53"},
                {"id": "ENSG00000012048", "approvedSymbol": "BRCA1"},
            ],
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(return_value=mock_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance):
                result = await execute_graphql_query(sample_query_string, jq_filter=".targets[] | .approvedSymbol")

        # Multiple results should be in result list
        assert result.status == QueryResultStatus.SUCCESS
        assert isinstance(result.result, list)
        assert result.result == ["TP53", "BRCA1"]
        mock_client_instance.execute_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_jq_filter_error_handling(self, sample_query_string):
        """Test that jq filter runtime errors are handled gracefully."""
        mock_response = {"target": {"id": "ENSG00000141510"}}

        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(return_value=mock_response)

        # Mock jq filter to raise an error during execution (not compilation)
        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance):
                with patch("open_targets_platform_mcp.client.graphql.jq.compile") as mock_jq_compile:
                    # Create a mock compiled filter that raises an error when used
                    mock_compiled_filter = AsyncMock()
                    mock_compiled_filter.input_value.return_value.all.side_effect = Exception("jq execution error")
                    mock_jq_compile.return_value = mock_compiled_filter

                    result = await execute_graphql_query(sample_query_string, jq_filter=".invalid_filter")

        # Should return warning with original data
        assert result.status == QueryResultStatus.WARNING
        assert result.result == mock_response
        assert "jq filter failed" in str(result.message)
        assert "// empty" in str(result.message)  # Should suggest null handling
        mock_client_instance.execute_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_jq_compilation_error(self, sample_query_string):
        """Test that jq compilation errors bubble up."""
        # Mock jq.compile to raise an error during compilation
        with patch("open_targets_platform_mcp.client.graphql.jq.compile") as mock_jq:
            mock_jq.side_effect = Exception("jq compilation error")

            with pytest.raises(Exception, match="jq compilation error"):
                await execute_graphql_query(sample_query_string, jq_filter=".invalid_filter")

    @pytest.mark.asyncio
    async def test_execute_query_no_jq_filter(self, sample_query_string, sample_graphql_response):
        """Test query execution without jq filter returns full response."""
        mock_client_instance = AsyncMock()
        mock_client_instance.execute_async = AsyncMock(return_value=sample_graphql_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client_instance):
                result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.result == sample_graphql_response
        mock_client_instance.execute_async.assert_awaited_once()


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
        assert "target" in result.result
        assert result.result["target"]["id"] == "ENSG00000141510"
        assert result.result["target"]["approvedSymbol"] == "TP53"

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
        assert result.result["target"]["id"] == "ENSG00000012048"
        assert result.result["target"]["approvedSymbol"] == "BRCA1"

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
        assert isinstance(result.result, list)
        assert result.result == ["TP53"]

    @pytest.mark.asyncio
    async def test_real_invalid_query(self):
        """Invalid query returns a structured error with hints, not an exception."""
        invalid_query = """
        query {
            nonexistentField {
                id
            }
        }
        """

        result = await execute_graphql_query(invalid_query)

        assert result.status == QueryResultStatus.ERROR
        assert result.message["error_type"] == "graphql_query_error"
        hints = result.message["hints"]
        assert len(hints) >= 1
        assert hints[0]["category"] == "unknown_root_query"
        assert hints[0]["field"] == "nonexistentField"

    @pytest.mark.asyncio
    async def test_real_unknown_field_on_target(self):
        """Pattern 1: unknown field on a known type with did_you_mean."""
        result = await execute_graphql_query(
            'query { target(ensemblId: "ENSG00000141510") { bogus } }',
        )

        assert result.status == QueryResultStatus.ERROR
        hint = result.message["hints"][0]
        assert hint["category"] == "unknown_field"
        assert hint["type"] == "Target"
        assert hint["field"] == "bogus"
        assert "approvedSymbol" in hint["available_fields"]

    @pytest.mark.asyncio
    async def test_real_unknown_argument(self):
        """Pattern 3: wrong arg name. The API also returns a separate Pattern 7
        error for the missing required `ensemblId`, so we expect two hints."""
        result = await execute_graphql_query(
            'query { target(id: "ENSG00000141510") { id } }',
        )

        assert result.status == QueryResultStatus.ERROR
        hints = result.message["hints"]
        categories = {h["category"] for h in hints}
        assert "unknown_argument" in categories
        assert "missing_required_argument" in categories
        unknown_arg = next(h for h in hints if h["category"] == "unknown_argument")
        assert unknown_arg["argument"] == "id"
        assert "ensemblId" in unknown_arg["available_arguments"]

    @pytest.mark.asyncio
    async def test_real_missing_subselection(self):
        """Pattern 5: scalar selection on a field that needs subselection."""
        result = await execute_graphql_query(
            'query { target(ensemblId: "ENSG00000141510") { proteinIds } }',
        )

        assert result.status == QueryResultStatus.ERROR
        hint = result.message["hints"][0]
        assert hint["category"] == "missing_subselection"
        assert hint["field"] == "proteinIds"
        assert hint["inner_type"] == "IdAndSource"

    @pytest.mark.asyncio
    async def test_real_undeclared_variable(self):
        """Pattern 7: variable used but not declared in the operation."""
        result = await execute_graphql_query(
            "query { target(ensemblId: $ensemblId) { id } }",
        )

        assert result.status == QueryResultStatus.ERROR
        hint = result.message["hints"][0]
        assert hint["category"] == "undeclared_variable"
        assert hint["variable"] == "ensemblId"


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
