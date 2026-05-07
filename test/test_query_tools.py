"""Tests for the query and batch_query tools (surface-level behavior)."""

from __future__ import annotations

import json

import pytest
from fastmcp.exceptions import ToolError

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
    async def test_returns_success_with_data(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "query_open_targets_graphql",
            {"query_string": _TARGET_QUERY, "variables": {"ensemblId": "ENSG00000139618"}},
        )
        data = json.loads(result.content[0].text)

        assert data["status"] == "success"
        assert data["data"] == {
            "target": {
                "id": "ENSG00000139618",
                "approvedSymbol": "BRCA2",
                "approvedName": "BRCA2 DNA repair associated",
            },
        }
        assert data["message"] is None

    @pytest.mark.asyncio
    async def test_no_variables(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool("query_open_targets_graphql", {"query_string": _META_QUERY})
        data = json.loads(result.content[0].text)

        assert data["status"] == "success"
        assert data["data"]["meta"]["name"] == "Open Targets GraphQL & REST API Beta"

    @pytest.mark.asyncio
    async def test_has_no_jq_filter_parameter(self, mcp_client_no_jq):
        tools = {t.name: t for t in await mcp_client_no_jq.list_tools()}
        props = tools["query_open_targets_graphql"].inputSchema.get("properties", {})
        assert "jq_filter" not in props

    @pytest.mark.asyncio
    async def test_jq_filter_is_rejected_as_unknown_parameter(self, mcp_client_no_jq):
        with pytest.raises(ToolError):
            await mcp_client_no_jq.call_tool(
                "query_open_targets_graphql",
                {
                    "query_string": _TARGET_QUERY,
                    "variables": {"ensemblId": "ENSG00000139618"},
                    "jq_filter": ".target.approvedSymbol",
                },
            )

    @pytest.mark.asyncio
    async def test_graphql_error_returns_error_result(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "query_open_targets_graphql",
            {"query_string": "query { nonExistentField }"},
        )
        data = json.loads(result.content[0].text)

        assert data["status"] == "error"
        assert "nonExistentField" in data["message"]

    @pytest.mark.asyncio
    async def test_malformed_query_returns_error_result(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "query_open_targets_graphql",
            {"query_string": "this is not { valid graphql"},
        )
        data = json.loads(result.content[0].text)

        assert data["status"] == "error"
        assert data["message"] is not None

    @pytest.mark.asyncio
    async def test_description_contains_args_and_return_info(self, mcp_client_no_jq):
        tools = {t.name: t for t in await mcp_client_no_jq.list_tools()}
        tool = tools["query_open_targets_graphql"]
        desc = tool.description

        assert "Args:" in desc
        assert "Returns:" in desc
        assert "query_string" in desc
        assert "variables" in desc
        assert "jq_filter" not in desc

    @pytest.mark.asyncio
    async def test_input_schema_marks_query_string_required_and_variables_optional(self, mcp_client_no_jq):
        tools = {t.name: t for t in await mcp_client_no_jq.list_tools()}
        schema = tools["query_open_targets_graphql"].inputSchema

        assert "query_string" in schema.get("required", [])
        assert "variables" not in schema.get("required", [])


# ---------------------------------------------------------------------------
# query_with_jq
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
    async def test_jq_filter_null_without_coalescing_returns_warning_with_null_tip(
        self,
        mcp_client_jq,
    ):
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
# batch_query_without_jq
# ---------------------------------------------------------------------------


class TestBatchQueryWithoutJq:
    @pytest.mark.asyncio
    async def test_single_variable_set(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "batch_query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables_list": [{"ensemblId": "ENSG00000139618"}],
                "key_field": "ensemblId",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["status_counts"]["total"] == 1
        assert data["status_counts"]["successful"] == 1
        assert data["status_counts"]["failed"] == 0
        assert data["results"][0]["id"] == "ENSG00000139618"
        assert data["results"][0]["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_multiple_variable_sets(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "batch_query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables_list": [
                    {"ensemblId": "ENSG00000139618"},
                    {"ensemblId": "ENSG00000141510"},
                ],
                "key_field": "ensemblId",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["status_counts"]["total"] == 2
        assert data["status_counts"]["successful"] == 2
        ids = {r["id"] for r in data["results"]}
        assert ids == {"ENSG00000139618", "ENSG00000141510"}

    @pytest.mark.asyncio
    async def test_missing_key_field_raises_tool_error(self, mcp_client_no_jq):
        with pytest.raises(ToolError, match="Key field"):
            await mcp_client_no_jq.call_tool(
                "batch_query_open_targets_graphql",
                {
                    "query_string": _TARGET_QUERY,
                    "variables_list": [{"wrongField": "ENSG00000139618"}],
                    "key_field": "ensemblId",
                },
            )

    @pytest.mark.asyncio
    async def test_graphql_error_in_one_item_does_not_affect_others(self, mcp_client_no_jq):
        # Cassette: ensemblId="ENSG00000139618" → success; ensemblId=12345 (int) → recorded error.
        # Both share the same query string; the type mismatch on the int value triggers a server error.
        result = await mcp_client_no_jq.call_tool(
            "batch_query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables_list": [
                    {"ensemblId": "ENSG00000139618"},
                    {"ensemblId": 12345},
                ],
                "key_field": "ensemblId",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["status_counts"]["total"] == 2
        assert data["status_counts"]["successful"] == 1
        assert data["status_counts"]["failed"] == 1
        successful = next(r for r in data["results"] if r["result"]["status"] == "success")
        assert successful["id"] == "ENSG00000139618"

    @pytest.mark.asyncio
    async def test_jq_filter_is_rejected_as_unknown_parameter(self, mcp_client_no_jq):
        with pytest.raises(ToolError):
            await mcp_client_no_jq.call_tool(
                "batch_query_open_targets_graphql",
                {
                    "query_string": _TARGET_QUERY,
                    "variables_list": [{"ensemblId": "ENSG00000139618"}],
                    "key_field": "ensemblId",
                    "jq_filter": ".target.approvedSymbol",
                },
            )

    @pytest.mark.asyncio
    async def test_malformed_query_marks_all_items_failed(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "batch_query_open_targets_graphql",
            {
                "query_string": "this is not { valid graphql",
                "variables_list": [
                    {"ensemblId": "ENSG00000139618"},
                    {"ensemblId": "ENSG00000141510"},
                ],
                "key_field": "ensemblId",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["status_counts"]["total"] == 2
        assert data["status_counts"]["successful"] == 0
        assert data["status_counts"]["failed"] == 2

    @pytest.mark.asyncio
    async def test_description_contains_args_and_return_info(self, mcp_client_no_jq):
        tools = {t.name: t for t in await mcp_client_no_jq.list_tools()}
        desc = tools["batch_query_open_targets_graphql"].description

        assert "Args:" in desc
        assert "Returns:" in desc
        assert "query_string" in desc
        assert "variables_list" in desc
        assert "key_field" in desc
        assert "jq_filter" not in desc

    @pytest.mark.asyncio
    async def test_unknown_id_returns_null_target_as_success(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "batch_query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables_list": [
                    {"ensemblId": "ENSG00000139618"},
                    {"ensemblId": "ENSG_UNKNOWN_DOES_NOT_EXIST"},
                ],
                "key_field": "ensemblId",
            },
        )
        data = json.loads(result.content[0].text)

        assert data["status_counts"]["total"] == 2
        assert data["status_counts"]["successful"] == 2
        assert data["status_counts"]["failed"] == 0
        unknown = next(r for r in data["results"] if r["id"] == "ENSG_UNKNOWN_DOES_NOT_EXIST")
        assert unknown["result"]["data"] == {"target": None}


# ---------------------------------------------------------------------------
# batch_query_with_jq
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
    async def test_has_jq_filter_parameter(self, mcp_client_jq):
        tools = {t.name: t for t in await mcp_client_jq.list_tools()}
        props = tools["batch_query_open_targets_graphql"].inputSchema.get("properties", {})
        assert "jq_filter" in props

    @pytest.mark.asyncio
    async def test_has_no_jq_filter_parameter_in_no_jq_mode(self, mcp_client_no_jq):
        tools = {t.name: t for t in await mcp_client_no_jq.list_tools()}
        props = tools["batch_query_open_targets_graphql"].inputSchema.get("properties", {})
        assert "jq_filter" not in props

    @pytest.mark.asyncio
    async def test_result_index_is_preserved(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "batch_query_open_targets_graphql",
            {
                "query_string": _TARGET_QUERY,
                "variables_list": [
                    {"ensemblId": "ENSG00000139618"},
                    {"ensemblId": "ENSG00000141510"},
                ],
                "key_field": "ensemblId",
            },
        )
        data = json.loads(result.content[0].text)

        indices = [r["index"] for r in data["results"]]
        assert indices == [0, 1]

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
    async def test_description_contains_jq_filter_with_null_coalescing_tip(self, mcp_client_jq):
        tools = {t.name: t for t in await mcp_client_jq.list_tools()}
        desc = tools["batch_query_open_targets_graphql"].description

        assert "jq_filter" in desc
        assert "//" in desc
