"""Tests for the schema and type_graph tools."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from open_targets_platform_mcp.tools.schema.schema import get_open_targets_graphql_schema
from open_targets_platform_mcp.tools.schema.type_graph import get_type_dependencies

# ---------------------------------------------------------------------------
# get_open_targets_graphql_schema
# ---------------------------------------------------------------------------


class TestGetOpenTargetsGraphqlSchema:
    @pytest.mark.asyncio
    async def test_valid_single_category_returns_sdl(self, mock_schema_caches):
        result = await get_open_targets_graphql_schema(["clinical-genetics"])

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_sdl_contains_expected_types(self, mock_schema_caches):
        result = await get_open_targets_graphql_schema(["clinical-genetics"])

        # clinical-genetics seeds include Disease and Target — they should appear
        assert "type Disease" in result or "Disease" in result
        assert "type Target" in result or "Target" in result

    @pytest.mark.asyncio
    async def test_common_mistakes_guide_appended(self, mock_schema_caches):
        result = await get_open_targets_graphql_schema(["clinical-genetics"])

        # The common_mistakes_guide.md content always ends up appended
        # It starts with a markdown heading
        assert "#" in result

    @pytest.mark.asyncio
    async def test_valid_multiple_categories(self, mock_schema_caches):
        result = await get_open_targets_graphql_schema(["clinical-genetics", "cancer-genomics"])

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_invalid_category_raises_tool_error(self, mock_schema_caches):
        with pytest.raises(ToolError) as exc_info:
            await get_open_targets_graphql_schema(["not-a-real-category"])

        assert "not-a-real-category" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_category_error_lists_valid_options(self, mock_schema_caches):
        with pytest.raises(ToolError) as exc_info:
            await get_open_targets_graphql_schema(["bogus"])

        # Error message should tell the caller what is available
        assert "clinical-genetics" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mix_valid_and_invalid_raises_tool_error(self, mock_schema_caches):
        with pytest.raises(ToolError):
            await get_open_targets_graphql_schema(["clinical-genetics", "bad-cat"])

    @pytest.mark.asyncio
    async def test_multiple_categories_produce_more_output_than_single(self, mock_schema_caches):
        single = await get_open_targets_graphql_schema(["clinical-genetics"])
        combined = await get_open_targets_graphql_schema(["clinical-genetics", "cancer-genomics"])

        # Combined result must be at least as long
        assert len(combined) >= len(single)


# ---------------------------------------------------------------------------
# get_type_dependencies
# ---------------------------------------------------------------------------


class TestGetTypeDependencies:
    @pytest.mark.asyncio
    async def test_single_valid_type_returns_sdl(self, mock_schema_caches):
        result = await get_type_dependencies(["Target"])

        assert isinstance(result, dict)
        assert "Target" in result
        assert isinstance(result["Target"], str)

    @pytest.mark.asyncio
    async def test_result_contains_shared_key(self, mock_schema_caches):
        result = await get_type_dependencies(["Target"])

        assert "shared" in result

    @pytest.mark.asyncio
    async def test_two_types_shared_types_separated(self, mock_schema_caches):
        result = await get_type_dependencies(["Target", "Drug"])

        # Both per-type keys present
        assert "Target" in result
        assert "Drug" in result
        assert "shared" in result

        # A type should not appear in both a per-type SDL and shared SDL
        # (basic sanity: no key appears in both Target-specific and shared)
        target_sdl = result["Target"]
        shared_sdl = result["shared"]
        # Pagination is a common utility type — if present it belongs in shared
        if "Pagination" in shared_sdl:
            assert "Pagination" not in target_sdl

    @pytest.mark.asyncio
    async def test_invalid_type_raises_tool_error(self, mock_schema_caches):
        with pytest.raises(ToolError) as exc_info:
            await get_type_dependencies(["NotARealType"])

        assert "NotARealType" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_type_error_suggests_similar(self, mock_schema_caches):
        with pytest.raises(ToolError) as exc_info:
            await get_type_dependencies(["Targ"])  # close to "Target"

        # Should suggest similar types in the error message
        assert "Target" in str(exc_info.value) or "Similar" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mix_valid_and_invalid_raises_tool_error(self, mock_schema_caches):
        with pytest.raises(ToolError):
            await get_type_dependencies(["Target", "AbsolutelyFakeType"])
