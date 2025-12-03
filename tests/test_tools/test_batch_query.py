"""Tests for batch query tool."""

from unittest.mock import patch

import pytest

from otar_mcp.tools.batch_query import _batch_query_impl

# Use the internal implementation function directly for testing
batch_query_fn = _batch_query_impl


class TestBatchQueryOpenTargetsGraphQL:
    """Tests for batch_query_open_targets_graphql function."""

    def test_batch_query_success(self, batch_query_string, batch_variables_with_key):
        """Test successful batch query execution."""
        # Mock execute_graphql_query to return success for each call
        with patch("otar_mcp.tools.batch_query.execute_graphql_query") as mock_execute:
            mock_execute.side_effect = [
                {"status": "success", "data": {"target": {"id": "ENSG00000141510", "approvedSymbol": "TP53"}}},
                {"status": "success", "data": {"target": {"id": "ENSG00000012048", "approvedSymbol": "BRCA1"}}},
                {"status": "success", "data": {"target": {"id": "ENSG00000139618", "approvedSymbol": "BRCA2"}}},
            ]

            result = batch_query_fn(
                query_string=batch_query_string, variables_list=batch_variables_with_key, key_field="ensemblId"
            )

        assert result["status"] == "success"
        assert "results" in result
        assert "summary" in result
        assert result["summary"]["total"] == 3
        assert result["summary"]["successful"] == 3
        assert result["summary"]["failed"] == 0

        # Check that results are keyed correctly
        assert "ENSG00000141510" in result["results"]
        assert "ENSG00000012048" in result["results"]
        assert "ENSG00000139618" in result["results"]

    def test_batch_query_empty_variables_list(self, batch_query_string):
        """Test that empty variables_list returns error."""
        result = batch_query_fn(query_string=batch_query_string, variables_list=[], key_field="ensemblId")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_batch_query_missing_key_field(self, batch_query_string):
        """Test handling when key_field is missing from variables."""
        variables_list = [
            {"ensemblId": "ENSG00000141510"},
            {"wrongField": "value"},  # Missing ensemblId
            {"ensemblId": "ENSG00000139618"},
        ]

        with patch("otar_mcp.tools.batch_query.execute_graphql_query") as mock_execute:
            mock_execute.side_effect = [
                {"status": "success", "data": {"target": {"id": "ENSG00000141510"}}},
                {"status": "success", "data": {"target": {"id": "ENSG00000139618"}}},
            ]

            result = batch_query_fn(
                query_string=batch_query_string, variables_list=variables_list, key_field="ensemblId"
            )

        assert result["status"] == "success"
        assert result["summary"]["total"] == 3
        assert result["summary"]["successful"] == 2
        assert result["summary"]["failed"] == 1

        # Check that missing key_field entry exists and has error
        assert "query_1" in result["results"]  # Fallback key
        assert result["results"]["query_1"]["status"] == "error"
        assert "not found" in result["results"]["query_1"]["message"]

    def test_batch_query_partial_failures(self, batch_query_string, batch_variables_with_key):
        """Test batch query with some queries failing."""
        with patch("otar_mcp.tools.batch_query.execute_graphql_query") as mock_execute:
            mock_execute.side_effect = [
                {"status": "success", "data": {"target": {"id": "ENSG00000141510"}}},
                {"status": "error", "message": "Query failed"},
                {"status": "success", "data": {"target": {"id": "ENSG00000139618"}}},
            ]

            result = batch_query_fn(
                query_string=batch_query_string, variables_list=batch_variables_with_key, key_field="ensemblId"
            )

        assert result["status"] == "success"
        assert result["summary"]["total"] == 3
        assert result["summary"]["successful"] == 2
        assert result["summary"]["failed"] == 1

        # Check the failed query result
        assert result["results"]["ENSG00000012048"]["status"] == "error"

    def test_batch_query_with_jq_filter(self, batch_query_string, batch_variables_with_key):
        """Test batch query with jq filter applied (when jq is enabled)."""
        jq_filter = ".data.target.approvedSymbol"

        with patch("otar_mcp.tools.batch_query.execute_graphql_query") as mock_execute:
            mock_execute.side_effect = [
                {"result": "TP53"},
                {"result": "BRCA1"},
                {"result": "BRCA2"},
            ]

            # Enable jq for this test
            with patch("otar_mcp.tools.batch_query.config") as mock_config:
                mock_config.jq_enabled = True
                mock_config.api_endpoint = "https://api.platform.opentargets.org/api/v4/graphql"

                result = batch_query_fn(
                    query_string=batch_query_string,
                    variables_list=batch_variables_with_key,
                    key_field="ensemblId",
                    jq_filter=jq_filter,
                )

        # Verify jq_filter was passed to execute_graphql_query
        assert mock_execute.call_count == 3
        for call in mock_execute.call_args_list:
            assert call[1]["jq_filter"] == jq_filter

        assert result["status"] == "success"

    def test_batch_query_jq_filter_ignored_when_disabled(self, batch_query_string, batch_variables_with_key):
        """Test that jq filter is ignored when jq is disabled."""
        jq_filter = ".data.target.approvedSymbol"

        with patch("otar_mcp.tools.batch_query.execute_graphql_query") as mock_execute:
            mock_execute.side_effect = [
                {"status": "success", "data": {"target": {"id": "ENSG00000141510"}}},
                {"status": "success", "data": {"target": {"id": "ENSG00000012048"}}},
                {"status": "success", "data": {"target": {"id": "ENSG00000139618"}}},
            ]

            # Disable jq for this test
            with patch("otar_mcp.tools.batch_query.config") as mock_config:
                mock_config.jq_enabled = False
                mock_config.api_endpoint = "https://api.platform.opentargets.org/api/v4/graphql"

                result = batch_query_fn(
                    query_string=batch_query_string,
                    variables_list=batch_variables_with_key,
                    key_field="ensemblId",
                    jq_filter=jq_filter,
                )

        # Verify jq_filter was NOT passed (should be None)
        assert mock_execute.call_count == 3
        for call in mock_execute.call_args_list:
            assert call[1]["jq_filter"] is None

        assert result["status"] == "success"

    def test_batch_query_exception_handling(self, batch_query_string, batch_variables_with_key):
        """Test that exceptions during individual query execution are caught."""
        with patch("otar_mcp.tools.batch_query.execute_graphql_query") as mock_execute:
            mock_execute.side_effect = [
                {"status": "success", "data": {"target": {"id": "ENSG00000141510"}}},
                Exception("Network error"),
                {"status": "success", "data": {"target": {"id": "ENSG00000139618"}}},
            ]

            result = batch_query_fn(
                query_string=batch_query_string, variables_list=batch_variables_with_key, key_field="ensemblId"
            )

        assert result["status"] == "success"
        assert result["summary"]["total"] == 3
        assert result["summary"]["successful"] == 2
        assert result["summary"]["failed"] == 1

        # Check the exception result
        failed_result = result["results"]["ENSG00000012048"]
        assert failed_result["status"] == "error"
        assert "Network error" in failed_result["message"]

    def test_batch_query_uses_config_endpoint(self, batch_query_string, batch_variables_with_key):
        """Test that batch query uses the config api_endpoint."""
        with patch("otar_mcp.tools.batch_query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"status": "success", "data": {}}

            with patch("otar_mcp.tools.batch_query.config") as mock_config:
                mock_config.api_endpoint = "https://test.api/graphql"
                mock_config.jq_enabled = False

                batch_query_fn(
                    query_string=batch_query_string, variables_list=[batch_variables_with_key[0]], key_field="ensemblId"
                )

            # Verify the endpoint was used
            call_args = mock_execute.call_args
            assert call_args[1]["endpoint_url"] == "https://test.api/graphql"

    def test_batch_query_sequential_execution(self, batch_query_string, batch_variables_with_key):
        """Test that queries are executed sequentially (not in parallel)."""
        call_order = []

        def track_call(endpoint_url, query_string, variables, jq_filter=None):
            call_order.append(variables["ensemblId"])
            return {"status": "success", "data": {}}

        with patch("otar_mcp.tools.batch_query.execute_graphql_query", side_effect=track_call):
            batch_query_fn(
                query_string=batch_query_string, variables_list=batch_variables_with_key, key_field="ensemblId"
            )

        # Verify queries were called in order
        assert call_order == ["ENSG00000141510", "ENSG00000012048", "ENSG00000139618"]

    def test_batch_query_result_structure(self, batch_query_string, batch_variables_with_key):
        """Test the structure of batch query results."""
        with patch("otar_mcp.tools.batch_query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"status": "success", "data": {"target": {"id": "test"}}}

            result = batch_query_fn(
                query_string=batch_query_string, variables_list=batch_variables_with_key, key_field="ensemblId"
            )

        # Check top-level structure
        assert "status" in result
        assert "results" in result
        assert "summary" in result

        # Check summary structure
        assert "total" in result["summary"]
        assert "successful" in result["summary"]
        assert "failed" in result["summary"]

        # Check that results is a dict keyed by the key_field value
        assert isinstance(result["results"], dict)

    def test_batch_query_jq_filter_warning(self, batch_query_string, batch_variables_with_key):
        """Test that jq filter warnings are preserved in results."""
        with patch("otar_mcp.tools.batch_query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {
                "status": "success",
                "data": {"target": {"id": "test"}},
                "warning": "jq filter failed: null value",
            }

            # Enable jq for this test
            with patch("otar_mcp.tools.batch_query.config") as mock_config:
                mock_config.jq_enabled = True
                mock_config.api_endpoint = "https://api.platform.opentargets.org/api/v4/graphql"

                result = batch_query_fn(
                    query_string=batch_query_string,
                    variables_list=[batch_variables_with_key[0]],
                    key_field="ensemblId",
                    jq_filter=".data.target.missing",
                )

        # The warning should still be in the result
        assert "warning" in result["results"]["ENSG00000141510"]
        assert result["summary"]["successful"] == 1  # Still counted as successful


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestBatchQueryIntegration:
    """Integration tests with real API calls."""

    def test_real_batch_query(self):
        """Test real batch query against OpenTargets API."""
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

        result = batch_query_fn(query_string=query, variables_list=variables_list, key_field="ensemblId")

        assert result["status"] == "success"
        assert result["summary"]["total"] == 2
        assert result["summary"]["successful"] == 2
        assert result["summary"]["failed"] == 0

        # Verify actual data
        assert result["results"]["ENSG00000141510"]["data"]["target"]["approvedSymbol"] == "TP53"
        assert result["results"]["ENSG00000012048"]["data"]["target"]["approvedSymbol"] == "BRCA1"

    def test_real_batch_query_with_jq_filter(self):
        """Test real batch query with jq filter (requires jq enabled)."""
        from otar_mcp.config import config

        # Enable jq for this integration test
        original_jq_enabled = config.jq_enabled
        config.jq_enabled = True

        try:
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

            result = batch_query_fn(
                query_string=query,
                variables_list=variables_list,
                key_field="ensemblId",
                jq_filter=".data.target.approvedSymbol",
            )

            assert result["status"] == "success"
            assert result["results"]["ENSG00000141510"]["result"] == "TP53"
            assert result["results"]["ENSG00000012048"]["result"] == "BRCA1"
        finally:
            # Restore original value
            config.jq_enabled = original_jq_enabled
