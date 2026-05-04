"""Tests for batch query tool."""

from unittest.mock import AsyncMock, call, patch

import pytest

from open_targets_platform_mcp.client import graphql as graphql_module
from open_targets_platform_mcp.model.result import BatchQueryResult, QueryResult, QueryResultStatus
from open_targets_platform_mcp.tools.batch_query.batch_query import _batch_query_impl

# Use the internal implementation function directly for testing
batch_query_fn = _batch_query_impl


@pytest.fixture(autouse=True)
def reset_graphql_session():
    """Reset the global gql session between tests."""
    graphql_module._runtime_state.client = None
    graphql_module._runtime_state.session = None
    yield
    graphql_module._runtime_state.client = None
    graphql_module._runtime_state.session = None


class TestBatchQueryOpenTargetsGraphQL:
    """Tests for batch_query_open_targets_graphql function."""

    @pytest.mark.asyncio
    async def test_batch_query_success(self, batch_query_string, batch_variables_with_key):
        """Test successful batch query execution."""
        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = [
                QueryResult.create_success({"target": {"id": "ENSG00000141510", "approvedSymbol": "TP53"}}),
                QueryResult.create_success({"target": {"id": "ENSG00000012048", "approvedSymbol": "BRCA1"}}),
                QueryResult.create_success({"target": {"id": "ENSG00000139618", "approvedSymbol": "BRCA2"}}),
            ]

            result = await batch_query_fn(
                query_string=batch_query_string,
                variables_list=batch_variables_with_key,
                key_field="ensemblId",
            )

        assert isinstance(result, BatchQueryResult)
        assert result.summary.total == 3
        assert result.summary.successful == 3
        assert result.summary.failed == 0

        # Check that results are in the list with correct keys
        result_dict = {r.key: r for r in result.results if r.key is not None}
        assert "ENSG00000141510" in result_dict
        assert "ENSG00000012048" in result_dict
        assert "ENSG00000139618" in result_dict
        assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_query_empty_variables_list(self, batch_query_string):
        """Test that empty variables_list returns error."""
        result = await batch_query_fn(query_string=batch_query_string, variables_list=[], key_field="ensemblId")

        assert isinstance(result, QueryResult)
        assert result.status == QueryResultStatus.ERROR
        assert "cannot be empty" in str(result.message)

    @pytest.mark.asyncio
    async def test_batch_query_missing_key_field(self, batch_query_string):
        """Test handling when key_field is missing from variables."""
        variables_list = [
            {"ensemblId": "ENSG00000141510"},
            {"wrongField": "value"},  # Missing ensemblId
            {"ensemblId": "ENSG00000139618"},
        ]

        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = [
                QueryResult.create_success({"target": {"id": "ENSG00000141510"}}),
                QueryResult.create_success({"target": {"id": "ENSG00000139618"}}),
            ]

            result = await batch_query_fn(
                query_string=batch_query_string,
                variables_list=variables_list,
                key_field="ensemblId",
            )

        assert isinstance(result, BatchQueryResult)
        assert result.summary.total == 3
        assert result.summary.successful == 2
        assert result.summary.failed == 1

        # Check that missing key_field entry exists and has error
        error_result = result.results[1]  # Index 1 is the one with missing key
        assert error_result.key is None
        assert error_result.result.status == QueryResultStatus.ERROR
        assert "not found" in str(error_result.result.message)
        assert mock_execute.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_query_partial_failures(self, batch_query_string, batch_variables_with_key):
        """Test batch query with some queries failing."""
        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = [
                QueryResult.create_success({"target": {"id": "ENSG00000141510"}}),
                QueryResult.create_error("Query failed"),
                QueryResult.create_success({"target": {"id": "ENSG00000139618"}}),
            ]

            result = await batch_query_fn(
                query_string=batch_query_string,
                variables_list=batch_variables_with_key,
                key_field="ensemblId",
            )

        assert isinstance(result, BatchQueryResult)
        assert result.summary.total == 3
        assert result.summary.successful == 2
        assert result.summary.failed == 1

        # Check the failed query result
        result_dict = {r.key: r for r in result.results if r.key is not None}
        assert result_dict["ENSG00000012048"].result.status == QueryResultStatus.ERROR

    @pytest.mark.asyncio
    async def test_batch_query_results_mapped_to_correct_keys(
        self,
        batch_query_string,
        batch_variables_with_key,
    ):
        """Each result must be mapped to the key from its own variables entry,
        including correct data for successes and error details for failures.
        """
        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = [
                QueryResult.create_success({"target": {"id": "ENSG00000141510", "approvedSymbol": "TP53"}}),
                QueryResult.create_error("Upstream error for BRCA1"),
                QueryResult.create_success({"target": {"id": "ENSG00000139618", "approvedSymbol": "BRCA2"}}),
            ]

            result = await batch_query_fn(
                query_string=batch_query_string,
                variables_list=batch_variables_with_key,
                key_field="ensemblId",
            )

        assert isinstance(result, BatchQueryResult)
        result_dict = {r.key: r for r in result.results}

        # Correct data for first entry
        tp53 = result_dict["ENSG00000141510"]
        assert tp53.result.status == QueryResultStatus.SUCCESS
        assert tp53.result.result["target"]["approvedSymbol"] == "TP53"

        # Error mapped to middle entry, not bleed into neighbours
        brca1 = result_dict["ENSG00000012048"]
        assert brca1.result.status == QueryResultStatus.ERROR
        assert "BRCA1" in str(brca1.result.message)

        # Correct data for last entry despite middle failure
        brca2 = result_dict["ENSG00000139618"]
        assert brca2.result.status == QueryResultStatus.SUCCESS
        assert brca2.result.result["target"]["approvedSymbol"] == "BRCA2"

        # Order in result list matches original input order
        assert [r.key for r in result.results] == [
            "ENSG00000141510",
            "ENSG00000012048",
            "ENSG00000139618",
        ]

    @pytest.mark.asyncio
    async def test_batch_query_with_jq_filter(self, batch_query_string, batch_variables_with_key):
        """Test batch query with jq filter applied."""
        jq_filter = ".data.target.approvedSymbol"

        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = [
                QueryResult.create_success("TP53"),
                QueryResult.create_success("BRCA1"),
                QueryResult.create_success("BRCA2"),
            ]

            result = await batch_query_fn(
                query_string=batch_query_string,
                variables_list=batch_variables_with_key,
                key_field="ensemblId",
                jq_filter=jq_filter,
            )

        # Verify jq_filter was passed to each query invocation
        expected_calls = [
            call(batch_query_string, variables, jq_filter=jq_filter) for variables in batch_variables_with_key
        ]
        mock_execute.assert_has_calls(expected_calls)
        assert mock_execute.call_count == 3

        assert isinstance(result, BatchQueryResult)
        assert result.summary.successful == 3

    @pytest.mark.asyncio
    async def test_batch_query_without_jq_filter(self, batch_query_string, batch_variables_with_key):
        """Test batch query without jq filter."""
        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = [
                QueryResult.create_success({"target": {"id": "ENSG00000141510"}}),
                QueryResult.create_success({"target": {"id": "ENSG00000012048"}}),
                QueryResult.create_success({"target": {"id": "ENSG00000139618"}}),
            ]

            result = await batch_query_fn(
                query_string=batch_query_string,
                variables_list=batch_variables_with_key,
                key_field="ensemblId",
                jq_filter=None,
            )

        # Verify jq_filter was passed as None to each query
        expected_calls = [call(batch_query_string, variables, jq_filter=None) for variables in batch_variables_with_key]
        mock_execute.assert_has_calls(expected_calls)
        assert mock_execute.call_count == 3

        assert isinstance(result, BatchQueryResult)
        assert result.summary.successful == 3

    @pytest.mark.asyncio
    async def test_batch_query_exception_handling(self, batch_query_string, batch_variables_with_key):
        """Test that error results during batch query execution are handled."""
        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = [
                QueryResult.create_success({"target": {"id": "ENSG00000141510"}}),
                QueryResult.create_error("Network error"),
                QueryResult.create_success({"target": {"id": "ENSG00000139618"}}),
            ]

            result = await batch_query_fn(
                query_string=batch_query_string,
                variables_list=batch_variables_with_key,
                key_field="ensemblId",
            )

        assert isinstance(result, BatchQueryResult)
        assert result.summary.total == 3
        assert result.summary.successful == 2
        assert result.summary.failed == 1

        # Check the error result
        result_dict = {r.key: r for r in result.results if r.key is not None}
        failed_result = result_dict["ENSG00000012048"]
        assert failed_result.result.status == QueryResultStatus.ERROR
        assert "Network error" in str(failed_result.result.message)

    @pytest.mark.asyncio
    async def test_batch_query_calls_execute_correctly(self, batch_query_string, batch_variables_with_key):
        """Test that batch query calls execute_graphql_query correctly."""
        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = QueryResult.create_success({})

            await batch_query_fn(
                query_string=batch_query_string,
                variables_list=[batch_variables_with_key[0]],
                key_field="ensemblId",
            )

            # Verify the function was called with correct arguments
            mock_execute.assert_called_once_with(
                batch_query_string,
                batch_variables_with_key[0],
                jq_filter=None,
            )

    @pytest.mark.asyncio
    async def test_batch_query_iterates_all_variables(self, batch_query_string, batch_variables_with_key):
        """Test that each variables entry is passed to execute_graphql_query."""
        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = [QueryResult.create_success({})] * 3

            await batch_query_fn(
                query_string=batch_query_string,
                variables_list=batch_variables_with_key,
                key_field="ensemblId",
            )

        # Verify each variables payload was passed in order
        expected_calls = [call(batch_query_string, variables, jq_filter=None) for variables in batch_variables_with_key]
        mock_execute.assert_has_calls(expected_calls)
        assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_query_result_structure(self, batch_query_string, batch_variables_with_key):
        """Test the structure of batch query results."""
        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = [
                QueryResult.create_success({"target": {"id": "test"}}),
                QueryResult.create_success({"target": {"id": "test"}}),
                QueryResult.create_success({"target": {"id": "test"}}),
            ]

            result = await batch_query_fn(
                query_string=batch_query_string,
                variables_list=batch_variables_with_key,
                key_field="ensemblId",
            )

        # Check top-level structure
        assert isinstance(result, BatchQueryResult)
        assert isinstance(result.results, list)
        assert isinstance(result.summary, type(result.summary))

        # Check summary structure
        assert hasattr(result.summary, "total")
        assert hasattr(result.summary, "successful")
        assert hasattr(result.summary, "failed")
        assert hasattr(result.summary, "warning")

    @pytest.mark.asyncio
    async def test_batch_query_jq_filter_warning(self, batch_query_string, batch_variables_with_key):
        """Test that jq filter warnings are preserved in results."""
        with patch(
            "open_targets_platform_mcp.tools.batch_query.batch_query.execute_graphql_query",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = QueryResult.create_warning(
                {"target": {"id": "test"}},
                "jq filter failed: null value",
            )

            result = await batch_query_fn(
                query_string=batch_query_string,
                variables_list=[batch_variables_with_key[0]],
                key_field="ensemblId",
                jq_filter=".data.target.missing",
            )

        # The warning should still be in the result
        result_dict = {r.key: r for r in result.results if r.key is not None}
        assert result_dict["ENSG00000141510"].result.status == QueryResultStatus.WARNING
        assert result.summary.warning == 1  # Counted as warning
        assert result.summary.successful == 0


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestBatchQueryIntegration:
    """Integration tests with real API calls."""

    @pytest.mark.asyncio
    async def test_real_batch_query_executes_per_item(self):
        """Batch helper should execute single-item queries and return a batch result."""
        query = """
        query GetTarget($ensemblId: String!) {
            target(ensemblId: $ensemblId) {
                id
                approvedSymbol
            }
        }
        """

        variables_list = [
            {"ensemblId": "ENSG00000141510"},
            {"ensemblId": "ENSG00000012048"},
        ]

        result = await batch_query_fn(query_string=query, variables_list=variables_list, key_field="ensemblId")

        assert isinstance(result, BatchQueryResult)
        assert result.summary.total == 2
        assert len(result.results) == 2
