"""Tests for query tool."""

from unittest.mock import AsyncMock, patch

import pytest

from open_targets_platform_mcp.model.result import QueryResult, QueryResultStatus
from open_targets_platform_mcp.settings import settings
from open_targets_platform_mcp.tools.query.query import _query_impl

# Use the internal implementation function directly for testing
query_fn = _query_impl


class TestQueryOpenTargetsGraphQL:
    """Tests for query_open_targets_graphql function."""

    @pytest.mark.asyncio
    async def test_query_returns_query_result(self, sample_query_string):
        """Test that query_open_targets_graphql returns a QueryResult."""
        with patch(
            "open_targets_platform_mcp.tools.query.query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = QueryResult.create_success({})

            result = await query_fn(sample_query_string)

        assert isinstance(result, QueryResult)

    @pytest.mark.asyncio
    async def test_query_success_without_variables(self, sample_query_string):
        """Test successful query execution without variables."""
        expected_data = {"target": {"id": "ENSG00000141510", "approvedSymbol": "TP53"}}
        expected_response = QueryResult.create_success(expected_data)

        with patch(
            "open_targets_platform_mcp.tools.query.query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = expected_response

            result = await query_fn(sample_query_string)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.result == expected_data
        mock_execute.assert_called_once_with(
            sample_query_string,
            None,
            jq_filter=None,
        )

    @pytest.mark.asyncio
    async def test_query_with_dict_variables(self, sample_query_string, sample_variables):
        """Test query execution with dict variables."""
        with patch(
            "open_targets_platform_mcp.tools.query.query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = QueryResult.create_success({})

            await query_fn(sample_query_string, variables=sample_variables)

        # Verify variables were passed as-is (dict)
        mock_execute.assert_called_once_with(
            sample_query_string,
            sample_variables,
            jq_filter=None,
        )

    @pytest.mark.asyncio
    async def test_query_with_none_variables(self, sample_query_string):
        """Test query with explicitly None variables."""
        with patch(
            "open_targets_platform_mcp.tools.query.query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = QueryResult.create_success({})

            await query_fn(sample_query_string, variables=None)

        # Verify None was passed
        mock_execute.assert_called_once_with(
            sample_query_string,
            None,
            jq_filter=None,
        )

    @pytest.mark.asyncio
    async def test_query_with_jq_filter(self, sample_query_string):
        """Test query execution with jq filter."""
        jq_filter = ".data.target.approvedSymbol"

        with patch(
            "open_targets_platform_mcp.tools.query.query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = QueryResult.create_success("TP53")

            await query_fn(sample_query_string, jq_filter=jq_filter)

        # Verify jq_filter was passed
        mock_execute.assert_called_once_with(
            sample_query_string,
            None,
            jq_filter=jq_filter,
        )

    @pytest.mark.asyncio
    async def test_query_exception_handling(self, sample_query_string):
        """Test that exceptions are bubbled up."""
        with patch(
            "open_targets_platform_mcp.tools.query.query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = Exception("Unexpected error")

            with pytest.raises(Exception, match="Unexpected error"):
                await query_fn(sample_query_string)

    @pytest.mark.asyncio
    async def test_query_with_all_parameters(self, sample_query_string, sample_variables):
        """Test query with all parameters provided."""
        jq_filter = ".data.target.id"

        with patch(
            "open_targets_platform_mcp.tools.query.query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = QueryResult.create_success("ENSG00000141510")

            await query_fn(sample_query_string, variables=sample_variables, jq_filter=jq_filter)

        # Verify all parameters were passed correctly
        mock_execute.assert_called_once_with(
            sample_query_string,
            sample_variables,
            jq_filter=jq_filter,
        )


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestQueryIntegration:
    """Integration tests with real API calls."""

    @pytest.mark.asyncio
    async def test_real_query_without_variables(self):
        """Test real query execution without variables."""
        query = """
        query {
            target(ensemblId: "ENSG00000141510") {
                id
                approvedSymbol
            }
        }
        """

        result = await query_fn(query)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.result is not None
        assert result.result["target"]["id"] == "ENSG00000141510"
        assert result.result["target"]["approvedSymbol"] == "TP53"

    @pytest.mark.asyncio
    async def test_real_query_with_dict_variables(self):
        """Test real query with dict variables."""
        query = """
        query GetTarget($ensemblId: String!) {
            target(ensemblId: $ensemblId) {
                id
                approvedSymbol
            }
        }
        """

        result = await query_fn(query, variables={"ensemblId": "ENSG00000012048"})

        assert result.status == QueryResultStatus.SUCCESS
        assert result.result is not None
        assert result.result["target"]["id"] == "ENSG00000012048"
        assert result.result["target"]["approvedSymbol"] == "BRCA1"

    @pytest.mark.asyncio
    async def test_real_query_with_jq_filter(self):
        """Test real query with jq filter (requires jq enabled)."""
        # Enable jq for this integration test
        original_jq_enabled = settings.jq_enabled
        settings.jq_enabled = True

        try:
            query = """
            query {
                target(ensemblId: "ENSG00000141510") {
                    id
                    approvedSymbol
                    approvedName
                }
            }
            """

            result = await query_fn(query, jq_filter=".target | {id, symbol: .approvedSymbol}")

            assert result.status == QueryResultStatus.SUCCESS
            assert result.result is not None
            # jq filter returns a list when processing the result
            assert isinstance(result.result, list)
            assert len(result.result) == 1
            assert isinstance(result.result[0], dict)
            assert "id" in result.result[0]
            assert "symbol" in result.result[0]
            assert result.result[0]["id"] == "ENSG00000141510"
            assert result.result[0]["symbol"] == "TP53"
        finally:
            # Restore original value
            settings.jq_enabled = original_jq_enabled
