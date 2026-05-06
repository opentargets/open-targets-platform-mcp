"""Tests for the search_entities tool."""

from __future__ import annotations

import pytest

from open_targets_platform_mcp.model.search_entities_result import SearchEntitiesFoundEntity
from open_targets_platform_mcp.tools.search_entities.search_entities import search_entities


class TestSearchEntities:
    @pytest.mark.asyncio
    async def test_single_query_returns_top_3_hits(self, mock_gql_session):
        result = await search_entities(["BRCA1"])

        assert "BRCA1" in result
        hits = result["BRCA1"]
        # At most 3 hits
        assert len(hits) <= 3
        # All are SearchEntitiesFoundEntity instances
        assert all(isinstance(h, SearchEntitiesFoundEntity) for h in hits)

    @pytest.mark.asyncio
    async def test_brca1_top_hit_is_target(self, mock_gql_session):
        result = await search_entities(["BRCA1"])

        first = result["BRCA1"][0]
        assert first.id == "ENSG00000012048"
        assert first.type == "target"

    @pytest.mark.asyncio
    async def test_aspirin_top_hit_is_drug(self, mock_gql_session):
        result = await search_entities(["aspirin"])

        first = result["aspirin"][0]
        assert first.id == "CHEMBL25"
        assert first.type == "drug"

    @pytest.mark.asyncio
    async def test_ibuprofen_top_hit_is_drug(self, mock_gql_session):
        result = await search_entities(["ibuprofen"])

        first = result["ibuprofen"][0]
        assert first.id == "CHEMBL521"
        assert first.type == "drug"

    @pytest.mark.asyncio
    async def test_multiple_queries_all_returned(self, mock_gql_session):
        result = await search_entities(["BRCA1", "aspirin"])

        assert set(result.keys()) == {"BRCA1", "aspirin"}

    @pytest.mark.asyncio
    async def test_multiple_queries_correct_hits(self, mock_gql_session):
        result = await search_entities(["BRCA1", "aspirin"])

        assert result["BRCA1"][0].id == "ENSG00000012048"
        assert result["aspirin"][0].id == "CHEMBL25"

    @pytest.mark.asyncio
    async def test_entity_fields_are_non_empty_strings(self, mock_gql_session):
        result = await search_entities(["ibuprofen"])

        for entity in result["ibuprofen"]:
            assert isinstance(entity.id, str) and entity.id
            assert isinstance(entity.type, str) and entity.type
