"""Tests for the schema and type_graph tools."""

from __future__ import annotations

import json

import pytest
from fastmcp.exceptions import ToolError

# ---------------------------------------------------------------------------
# get_open_targets_graphql_schema
# ---------------------------------------------------------------------------


class TestGetOpenTargetsGraphqlSchema:
    @pytest.mark.asyncio
    async def test_valid_single_category_returns_sdl(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "get_open_targets_graphql_schema",
            {"categories": ["clinical-genetics"]},
        )

        assert isinstance(result.content[0].text, str)
        assert len(result.content[0].text) > 0

    @pytest.mark.asyncio
    async def test_sdl_contains_expected_types(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "get_open_targets_graphql_schema",
            {"categories": ["clinical-genetics"]},
        )
        sdl = result.content[0].text

        assert "Disease" in sdl
        assert "Target" in sdl

    @pytest.mark.asyncio
    async def test_common_mistakes_guide_appended(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "get_open_targets_graphql_schema",
            {"categories": ["clinical-genetics"]},
        )

        assert "#" in result.content[0].text

    @pytest.mark.asyncio
    async def test_valid_multiple_categories(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "get_open_targets_graphql_schema",
            {"categories": ["clinical-genetics", "cancer-genomics"]},
        )

        assert isinstance(result.content[0].text, str)
        assert len(result.content[0].text) > 0

    @pytest.mark.asyncio
    async def test_invalid_category_raises_tool_error(self, mcp_client_no_jq):
        with pytest.raises(ToolError) as exc_info:
            await mcp_client_no_jq.call_tool(
                "get_open_targets_graphql_schema",
                {"categories": ["not-a-real-category"]},
            )

        assert "not-a-real-category" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_category_error_lists_valid_options(self, mcp_client_no_jq):
        with pytest.raises(ToolError) as exc_info:
            await mcp_client_no_jq.call_tool(
                "get_open_targets_graphql_schema",
                {"categories": ["bogus"]},
            )

        assert "clinical-genetics" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mix_valid_and_invalid_raises_tool_error(self, mcp_client_no_jq):
        with pytest.raises(ToolError):
            await mcp_client_no_jq.call_tool(
                "get_open_targets_graphql_schema",
                {"categories": ["clinical-genetics", "bad-cat"]},
            )

    @pytest.mark.asyncio
    async def test_multiple_categories_produce_more_output_than_single(self, mcp_client_no_jq):
        single = await mcp_client_no_jq.call_tool(
            "get_open_targets_graphql_schema",
            {"categories": ["clinical-genetics"]},
        )
        combined = await mcp_client_no_jq.call_tool(
            "get_open_targets_graphql_schema",
            {"categories": ["clinical-genetics", "cancer-genomics"]},
        )

        assert len(combined.content[0].text) >= len(single.content[0].text)


# ---------------------------------------------------------------------------
# get_type_dependencies
# ---------------------------------------------------------------------------


class TestGetTypeDependencies:
    @pytest.mark.asyncio
    async def test_single_valid_type_returns_sdl(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "get_type_dependencies",
            {"type_names": ["Target"]},
        )
        data = json.loads(result.content[0].text)

        assert isinstance(data, dict)
        assert "Target" in data
        assert isinstance(data["Target"], str)

    @pytest.mark.asyncio
    async def test_result_contains_shared_key(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "get_type_dependencies",
            {"type_names": ["Target"]},
        )
        data = json.loads(result.content[0].text)

        assert "shared" in data

    @pytest.mark.asyncio
    async def test_two_types_shared_types_separated(self, mcp_client_no_jq):
        result = await mcp_client_no_jq.call_tool(
            "get_type_dependencies",
            {"type_names": ["Target", "Drug"]},
        )
        data = json.loads(result.content[0].text)

        assert "Target" in data
        assert "Drug" in data
        assert "shared" in data

        target_sdl = data["Target"]
        shared_sdl = data["shared"]
        if "Pagination" in shared_sdl:
            assert "Pagination" not in target_sdl

    @pytest.mark.asyncio
    async def test_invalid_type_raises_tool_error(self, mcp_client_no_jq):
        with pytest.raises(ToolError) as exc_info:
            await mcp_client_no_jq.call_tool(
                "get_type_dependencies",
                {"type_names": ["NotARealType"]},
            )

        assert "NotARealType" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_type_error_suggests_similar(self, mcp_client_no_jq):
        with pytest.raises(ToolError) as exc_info:
            await mcp_client_no_jq.call_tool("get_type_dependencies", {"type_names": ["Targ"]})

        assert "Target" in str(exc_info.value) or "Similar" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mix_valid_and_invalid_raises_tool_error(self, mcp_client_no_jq):
        with pytest.raises(ToolError):
            await mcp_client_no_jq.call_tool(
                "get_type_dependencies",
                {"type_names": ["Target", "AbsolutelyFakeType"]},
            )


# ---------------------------------------------------------------------------
# categories.json integrity
# ---------------------------------------------------------------------------


class TestCategoriesIntegrity:
    def test_all_category_types_exist_in_schema(self, graphql_schema, mock_schema_caches):
        import json
        from pathlib import Path

        categories_path = (
            Path(__file__).parent.parent / "src" / "open_targets_platform_mcp" / "assets" / "categories.json"
        )
        categories = json.loads(categories_path.read_text(encoding="utf-8"))
        schema_type_map = graphql_schema.type_map

        missing: list[str] = []
        for category, data in categories.items():
            for type_name in data["types"]:
                if type_name not in schema_type_map:
                    missing.append(f"{category}: {type_name}")

        assert missing == [], "Types listed in categories.json are absent from the schema:\n" + "\n".join(missing)
