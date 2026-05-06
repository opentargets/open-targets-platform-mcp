"""Tests for the query and batch_query tools (surface-level behavior)."""

from __future__ import annotations

import inspect

import pytest

from open_targets_platform_mcp.model.query_result import BatchQueryResult, QueryResultStatus
from open_targets_platform_mcp.tools.batch_query.batch_query import (
    batch_query_with_jq,
    batch_query_without_jq,
)
from open_targets_platform_mcp.tools.query.query import query_with_jq, query_without_jq

# ---------------------------------------------------------------------------
# Queries used across tests
# ---------------------------------------------------------------------------

_TARGET_QUERY = """
query TargetQuery($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    approvedName
  }
}
"""

_META_QUERY = """
query {
  meta {
    name
    apiVersion { x y z }
    dataVersion { year month iteration }
  }
}
"""


# ---------------------------------------------------------------------------
# query_without_jq
# ---------------------------------------------------------------------------


class TestQueryWithoutJq:
    @pytest.mark.asyncio
    async def test_returns_success_with_data(self, mock_gql_session):
        result = await query_without_jq(
            query_string=_TARGET_QUERY,
            variables={"ensemblId": "ENSG00000139618"},
        )

        assert result.status == QueryResultStatus.SUCCESS
        assert result.data == {
            "target": {
                "id": "ENSG00000139618",
                "approvedSymbol": "BRCA2",
                "approvedName": "BRCA2 DNA repair associated",
            },
        }
        assert result.message is None

    @pytest.mark.asyncio
    async def test_no_variables(self, mock_gql_session):
        result = await query_without_jq(query_string=_META_QUERY)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.data["meta"]["name"] == "Open Targets GraphQL & REST API Beta"

    def test_has_no_jq_filter_parameter(self):
        sig = inspect.signature(query_without_jq)
        assert "jq_filter" not in sig.parameters

    @pytest.mark.asyncio
    async def test_graphql_error_returns_error_result(self, mock_gql_session):
        """Unknown query produces a cassette miss → session raises → ERROR result."""
        result = await query_without_jq(query_string="query { nonExistentField }")

        assert result.status == QueryResultStatus.ERROR
        assert result.message is not None


# ---------------------------------------------------------------------------
# query_with_jq
# ---------------------------------------------------------------------------


class TestQueryWithJq:
    @pytest.mark.asyncio
    async def test_jq_filter_extracts_field(self, mock_gql_session):
        result = await query_with_jq(
            query_string=_TARGET_QUERY,
            variables={"ensemblId": "ENSG00000139618"},
            jq_filter=".target.approvedSymbol",
        )

        assert result.status == QueryResultStatus.SUCCESS
        assert result.data == ["BRCA2"]

    @pytest.mark.asyncio
    async def test_invalid_jq_filter_returns_warning_with_original_data(self, mock_gql_session):
        # A filter that compiles but fails at runtime: `error` raises a jq error
        # when executed, causing _apply_optional_filter to return WARNING.
        result = await query_with_jq(
            query_string=_TARGET_QUERY,
            variables={"ensemblId": "ENSG00000139618"},
            jq_filter=". | error",
        )

        assert result.status == QueryResultStatus.WARNING
        # Original data preserved
        assert result.data is not None
        assert "target" in result.data
        # Warning message is informative
        assert result.message is not None
        assert "jq filter failed" in result.message

    @pytest.mark.asyncio
    async def test_bad_jq_syntax_returns_error(self, mock_gql_session):
        """A jq compilation error (syntax error) surfaces as ERROR status."""
        result = await query_with_jq(
            query_string=_TARGET_QUERY,
            variables={"ensemblId": "ENSG00000139618"},
            jq_filter="!!!invalid jq",
        )

        assert result.status == QueryResultStatus.ERROR

    def test_has_jq_filter_parameter(self):
        sig = inspect.signature(query_with_jq)
        assert "jq_filter" in sig.parameters


# ---------------------------------------------------------------------------
# batch_query_without_jq
# ---------------------------------------------------------------------------


class TestBatchQueryWithoutJq:
    @pytest.mark.asyncio
    async def test_single_variable_set(self, mock_gql_session):
        result = await batch_query_without_jq(
            query_string=_TARGET_QUERY,
            variables_list=[{"ensemblId": "ENSG00000139618"}],
            key_field="ensemblId",
        )

        assert isinstance(result, BatchQueryResult)
        assert result.status_counts.total == 1
        assert result.status_counts.successful == 1
        assert result.status_counts.failed == 0
        assert result.results[0].id == "ENSG00000139618"
        assert result.results[0].result.status == QueryResultStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_multiple_variable_sets(self, mock_gql_session):
        result = await batch_query_without_jq(
            query_string=_TARGET_QUERY,
            variables_list=[
                {"ensemblId": "ENSG00000139618"},
                {"ensemblId": "ENSG00000141510"},
            ],
            key_field="ensemblId",
        )

        assert result.status_counts.total == 2
        assert result.status_counts.successful == 2
        ids = {r.id for r in result.results}
        assert ids == {"ENSG00000139618", "ENSG00000141510"}

    @pytest.mark.asyncio
    async def test_missing_key_field_raises_tool_error(self, mock_gql_session):
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="Key field"):
            await batch_query_without_jq(
                query_string=_TARGET_QUERY,
                variables_list=[{"wrongField": "ENSG00000139618"}],
                key_field="ensemblId",
            )

    @pytest.mark.asyncio
    async def test_unknown_id_returns_null_target_as_success(self, mock_gql_session):
        # A valid Ensembl ID that does not correspond to any target returns
        # {"target": null} — a valid GraphQL response, counted as success.
        result = await batch_query_without_jq(
            query_string=_TARGET_QUERY,
            variables_list=[
                {"ensemblId": "ENSG00000139618"},
                {"ensemblId": "ENSG_UNKNOWN_DOES_NOT_EXIST"},
            ],
            key_field="ensemblId",
        )

        assert result.status_counts.total == 2
        assert result.status_counts.successful == 2
        assert result.status_counts.failed == 0
        unknown = next(r for r in result.results if r.id == "ENSG_UNKNOWN_DOES_NOT_EXIST")
        assert unknown.result.data == {"target": None}

    def test_has_no_jq_filter_parameter(self):
        sig = inspect.signature(batch_query_without_jq)
        assert "jq_filter" not in sig.parameters

    @pytest.mark.asyncio
    async def test_result_index_is_preserved(self, mock_gql_session):
        result = await batch_query_without_jq(
            query_string=_TARGET_QUERY,
            variables_list=[
                {"ensemblId": "ENSG00000139618"},
                {"ensemblId": "ENSG00000141510"},
            ],
            key_field="ensemblId",
        )
        indices = [r.index for r in result.results]
        assert indices == [0, 1]


# ---------------------------------------------------------------------------
# batch_query_with_jq
# ---------------------------------------------------------------------------


class TestBatchQueryWithJq:
    @pytest.mark.asyncio
    async def test_jq_filter_applied_to_each_result(self, mock_gql_session):
        result = await batch_query_with_jq(
            query_string=_TARGET_QUERY,
            variables_list=[
                {"ensemblId": "ENSG00000139618"},
                {"ensemblId": "ENSG00000141510"},
            ],
            key_field="ensemblId",
            jq_filter=".target.approvedSymbol",
        )

        assert result.status_counts.successful == 2
        symbols = {r.id: r.result.data for r in result.results}
        assert symbols["ENSG00000139618"] == ["BRCA2"]
        assert symbols["ENSG00000141510"] == ["TP53"]

    def test_has_jq_filter_parameter(self):
        sig = inspect.signature(batch_query_with_jq)
        assert "jq_filter" in sig.parameters
