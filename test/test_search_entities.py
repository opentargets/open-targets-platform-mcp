"""Tests for the search_entities tool."""

from __future__ import annotations

import json

import pytest


class TestSearchEntities:
    @pytest.mark.asyncio
    async def test_single_query_returns_top_3_hits(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool("search_entities", {"query_strings": ["BRCA1"]})
        data = json.loads(result.content[0].text)

        assert "BRCA1" in data
        hits = data["BRCA1"]
        assert len(hits) <= 3
        assert all(isinstance(h, dict) and "id" in h and "type" in h for h in hits)

    @pytest.mark.asyncio
    async def test_brca1_top_hit_is_target(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool("search_entities", {"query_strings": ["BRCA1"]})
        data = json.loads(result.content[0].text)

        first = data["BRCA1"][0]
        assert first["id"] == "ENSG00000012048"
        assert first["type"] == "target"

    @pytest.mark.asyncio
    async def test_aspirin_top_hit_is_drug(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool("search_entities", {"query_strings": ["aspirin"]})
        data = json.loads(result.content[0].text)

        first = data["aspirin"][0]
        assert first["id"] == "CHEMBL25"
        assert first["type"] == "drug"

    @pytest.mark.asyncio
    async def test_ibuprofen_top_hit_is_drug(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool("search_entities", {"query_strings": ["ibuprofen"]})
        data = json.loads(result.content[0].text)

        first = data["ibuprofen"][0]
        assert first["id"] == "CHEMBL521"
        assert first["type"] == "drug"

    @pytest.mark.asyncio
    async def test_multiple_queries_all_returned(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "search_entities",
            {"query_strings": ["BRCA1", "aspirin"]},
        )
        data = json.loads(result.content[0].text)

        assert set(data.keys()) == {"BRCA1", "aspirin"}

    @pytest.mark.asyncio
    async def test_multiple_queries_correct_hits(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "search_entities",
            {"query_strings": ["BRCA1", "aspirin"]},
        )
        data = json.loads(result.content[0].text)

        assert data["BRCA1"][0]["id"] == "ENSG00000012048"
        assert data["aspirin"][0]["id"] == "CHEMBL25"

    @pytest.mark.asyncio
    async def test_entity_fields_are_non_empty_strings(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool("search_entities", {"query_strings": ["ibuprofen"]})
        data = json.loads(result.content[0].text)

        for entity in data["ibuprofen"]:
            assert isinstance(entity["id"], str) and entity["id"]
            assert isinstance(entity["type"], str) and entity["type"]
