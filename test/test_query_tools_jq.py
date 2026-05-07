"""Tests for query and batch_query tools with jq enabled."""

from __future__ import annotations

import json

import pytest

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


# ---------------------------------------------------------------------------
# query_open_targets_graphql — jq enabled
# ---------------------------------------------------------------------------


class TestQueryWithJq:
    @pytest.mark.asyncio
    async def test_jq_filter_extracts_field(self, mcp_client_jq):
        result = await mcp_client_jq.call_tool(
            "query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables": {"ensemblId": "ENSG00000139618"},
                "jq_filter": ".target.approvedSymbol",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["status"] == "success"
        assert data["data"] == ["BRCA2"]

    @pytest.mark.asyncio
    async def test_invalid_jq_filter_returns_warning_with_original_data(self, mcp_client_jq):
        result = await mcp_client_jq.call_tool(
            "query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables": {"ensemblId": "ENSG00000139618"},
                "jq_filter": ". | error",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["status"] == "warning"
        assert data["data"] is not None
        assert "target" in data["data"]
        assert data["message"] is not None
        assert "jq filter failed" in data["message"]

    @pytest.mark.asyncio
    async def test_jq_filter_null_without_coalescing_returns_warning_with_null_tip(self, mcp_client_jq):
        # query returns {"target": null} for unknown ID; ascii_upcase on null triggers jq error
        result = await mcp_client_jq.call_tool(
            "query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables": {"ensemblId": "ENSG_UNKNOWN_DOES_NOT_EXIST"},
                "jq_filter": ".target.approvedSymbol | ascii_upcase",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["status"] == "warning"
        assert data["data"] == {"target": None}
        assert "//" in data["message"]

    @pytest.mark.asyncio
    async def test_bad_jq_syntax_returns_error(self, mcp_client_jq):
        result = await mcp_client_jq.call_tool(
            "query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables": {"ensemblId": "ENSG00000139618"},
                "jq_filter": "!!!invalid jq",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_malformed_query_returns_error_result(self, mcp_client_jq):
        result = await mcp_client_jq.call_tool(
            "query_open_targets_graphql",
            {"query_string": "this is not { valid graphql"},
        )
        data = json.loads(result.content[0].text)

        assert data["status"] == "error"
        assert data["message"] is not None

    @pytest.mark.asyncio
    async def test_has_jq_filter_parameter(self, mcp_client_jq):
        tools = {t.name: t for t in await mcp_client_jq.list_tools()}
        props = tools["query_open_targets_graphql"].inputSchema.get("properties", {})
        assert "jq_filter" in props

    @pytest.mark.asyncio
    async def test_description_contains_jq_filter_with_null_coalescing_tip(self, mcp_client_jq):
        tools = {t.name: t for t in await mcp_client_jq.list_tools()}
        desc = tools["query_open_targets_graphql"].description

        assert "jq_filter" in desc
        assert "//" in desc


# ---------------------------------------------------------------------------
# batch_query_open_targets_graphql — jq enabled
# ---------------------------------------------------------------------------


class TestBatchQueryWithJq:
    @pytest.mark.asyncio
    async def test_jq_filter_extracts_field(self, mcp_client_jq):
        result = await mcp_client_jq.call_tool(
            "batch_query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables_list": [{"ensemblId": "ENSG00000139618"}],
                "key_field": "ensemblId",
                "jq_filter": ".target.approvedSymbol",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["results"][0]["result"]["status"] == "success"
        assert data["results"][0]["result"]["data"] == ["BRCA2"]

    @pytest.mark.asyncio
    async def test_invalid_jq_filter_returns_warning(self, mcp_client_jq):
        result = await mcp_client_jq.call_tool(
            "batch_query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables_list": [{"ensemblId": "ENSG00000139618"}],
                "key_field": "ensemblId",
                "jq_filter": ". | error",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["results"][0]["result"]["status"] == "warning"
        assert data["results"][0]["result"]["data"] is not None

    @pytest.mark.asyncio
    async def test_jq_null_without_coalescing_returns_warning_with_null_tip(self, mcp_client_jq):
        # query returns {"target": null} for unknown ID; ascii_upcase on null triggers jq error
        result = await mcp_client_jq.call_tool(
            "batch_query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables_list": [{"ensemblId": "ENSG_UNKNOWN_DOES_NOT_EXIST"}],
                "key_field": "ensemblId",
                "jq_filter": ".target.approvedSymbol | ascii_upcase",
            },
        )
        data = json.loads(result.content[0].text)

        item = data["results"][0]
        assert item["result"]["status"] == "warning"
        assert "//" in item["result"]["message"]

    @pytest.mark.asyncio
    async def test_malformed_query_marks_all_items_failed(self, mcp_client_jq):
        result = await mcp_client_jq.call_tool(
            "batch_query_open_targets_graphql",
            {
                "query_string": "this is not { valid graphql",
                "variables_list": [
                    {"ensemblId": "ENSG00000139618"},
                    {"ensemblId": "ENSG00000141510"},
                ],
                "key_field": "ensemblId",
                "jq_filter": ".target.approvedSymbol",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["status_counts"]["total"] == 2
        assert data["status_counts"]["successful"] == 0
        assert data["status_counts"]["failed"] == 2

    @pytest.mark.asyncio
    async def test_has_jq_filter_parameter(self, mcp_client_jq):
        tools = {t.name: t for t in await mcp_client_jq.list_tools()}
        props = tools["batch_query_open_targets_graphql"].inputSchema.get("properties", {})
        assert "jq_filter" in props

    @pytest.mark.asyncio
    async def test_description_contains_jq_filter_arg(self, mcp_client_jq):
        tools = {t.name: t for t in await mcp_client_jq.list_tools()}
        desc = tools["batch_query_open_targets_graphql"].description

        assert "jq_filter" in desc
