"""Tests for subschema module."""

from unittest.mock import AsyncMock, patch

import pytest
from graphql import build_schema

from open_targets_platform_mcp.tools.schema import subschema, type_graph


@pytest.fixture
def clear_cache():
    """Clear all caches before and after each test."""
    type_graph._cached_type_graph = None
    type_graph._cached_schema = None
    subschema._cached_subschemas = None
    yield
    type_graph._cached_type_graph = None
    type_graph._cached_schema = None
    subschema._cached_subschemas = None


@pytest.fixture
def mock_graphql_schema():
    """Create a mock GraphQL schema for testing."""
    return build_schema(
        """
        type Query {
            target(ensemblId: String!): Target
            disease(efoId: String!): Disease
        }

        type Target {
            id: String!
            approvedSymbol: String
            diseases: [Disease!]
            pathways: [Pathway!]
        }

        type Disease {
            id: String!
            name: String
            targets: [Target!]
            drugs: [Drug!]
        }

        type Drug {
            id: String!
            name: String
            mechanisms: [Mechanism!]
        }

        type Pathway {
            id: String!
            name: String
        }

        type Mechanism {
            id: String!
            description: String
        }

        type Pagination {
            count: Int!
        }

        enum DiseaseType {
            RARE
            COMMON
        }

        union SearchResult = Target | Disease | Drug
        """,
    )


@pytest.fixture
def mock_categories():
    """Create mock categories for testing."""
    return {
        "target-info": {
            "description": "Target information and pathways",
            "types": ["Target", "Pathway"],
        },
        "disease-info": {
            "description": "Disease information and drugs",
            "types": ["Disease", "Drug"],
        },
        "shared-types": {
            "description": "Common shared types",
            "types": ["Pagination"],
        },
    }


class TestLoadCategories:
    """Tests for _load_categories function."""

    def test_loads_categories(self):
        """Should load categories from JSON file."""
        categories = subschema._load_categories()
        assert isinstance(categories, dict)
        # Should have at least some categories
        assert len(categories) > 0

    def test_category_has_description(self):
        """Each category should have a description."""
        categories = subschema._load_categories()
        for name, data in categories.items():
            assert "description" in data
            assert isinstance(data["description"], str)

    def test_category_has_types(self):
        """Each category should have types list."""
        categories = subschema._load_categories()
        for name, data in categories.items():
            assert "types" in data
            assert isinstance(data["types"], list)


class TestGetReachableTypesWithDepth:
    """Tests for get_reachable_types_with_depth function."""

    def test_depth_zero_returns_seed_only(self, mock_graphql_schema):
        """Depth 0 should return only seed types."""
        graph = type_graph.build_type_graph(mock_graphql_schema)
        reachable = type_graph.get_reachable_types_with_depth(
            graph, {"Target"}, max_depth=0
        )
        assert reachable == {"Target"}

    def test_depth_one_returns_direct_refs(self, mock_graphql_schema):
        """Depth 1 should include direct references only."""
        graph = type_graph.build_type_graph(mock_graphql_schema)
        reachable = type_graph.get_reachable_types_with_depth(
            graph, {"Target"}, max_depth=1
        )
        # Target references Disease and Pathway directly
        assert "Target" in reachable
        assert "Disease" in reachable
        assert "Pathway" in reachable
        # Drug is only reachable via Disease (depth 2)
        assert "Drug" not in reachable

    def test_depth_two_includes_transitive(self, mock_graphql_schema):
        """Depth 2 should include types at depth 2."""
        graph = type_graph.build_type_graph(mock_graphql_schema)
        reachable = type_graph.get_reachable_types_with_depth(
            graph, {"Target"}, max_depth=2
        )
        # Target -> Disease -> Drug (depth 2)
        assert "Drug" in reachable
        # Target -> Disease -> Drug -> Mechanism (depth 3)
        assert "Mechanism" not in reachable

    def test_depth_none_is_exhaustive(self, mock_graphql_schema):
        """None depth should traverse all reachable types."""
        graph = type_graph.build_type_graph(mock_graphql_schema)
        reachable = type_graph.get_reachable_types_with_depth(
            graph, {"Target"}, max_depth=None
        )
        # Should find all transitively reachable types
        assert "Target" in reachable
        assert "Disease" in reachable
        assert "Pathway" in reachable
        assert "Drug" in reachable
        assert "Mechanism" in reachable

    def test_multiple_seed_types(self, mock_graphql_schema):
        """Should handle multiple seed types correctly."""
        graph = type_graph.build_type_graph(mock_graphql_schema)
        reachable = type_graph.get_reachable_types_with_depth(
            graph, {"Pathway", "Mechanism"}, max_depth=1
        )
        # Both should be included
        assert "Pathway" in reachable
        assert "Mechanism" in reachable
        # Neither has outgoing refs, so size should be 2
        assert len(reachable) == 2

    def test_handles_cycles(self, mock_graphql_schema):
        """Should handle cycles without infinite loop."""
        graph = type_graph.build_type_graph(mock_graphql_schema)
        # Target <-> Disease is a cycle
        reachable = type_graph.get_reachable_types_with_depth(
            graph, {"Target"}, max_depth=10
        )
        # Should not infinite loop
        assert "Target" in reachable
        assert "Disease" in reachable


class TestBuildCategorySubschema:
    """Tests for _build_category_subschema function."""

    def test_builds_subschema_with_depth(self, mock_graphql_schema, mock_categories):
        """Should build subschema with specified depth."""
        graph = type_graph.build_type_graph(mock_graphql_schema)
        cat_subschema = subschema._build_category_subschema(
            "target-info",
            mock_categories["target-info"],
            graph,
            mock_graphql_schema,
            depth=1,
        )

        assert cat_subschema.name == "target-info"
        assert cat_subschema.description == "Target information and pathways"
        # Seed types: Target, Pathway
        # Depth 1: Target -> Disease, Pathway (no outgoing)
        assert "Target" in cat_subschema.types
        assert "Pathway" in cat_subschema.types
        assert "Disease" in cat_subschema.types
        # Drug is depth 2 from Target
        assert "Drug" not in cat_subschema.types

    def test_builds_subschema_exhaustive(self, mock_graphql_schema, mock_categories):
        """Should build exhaustive subschema."""
        graph = type_graph.build_type_graph(mock_graphql_schema)
        cat_subschema = subschema._build_category_subschema(
            "target-info",
            mock_categories["target-info"],
            graph,
            mock_graphql_schema,
            depth="exhaustive",
        )

        # Should include all transitively reachable types
        assert "Target" in cat_subschema.types
        assert "Pathway" in cat_subschema.types
        assert "Disease" in cat_subschema.types
        assert "Drug" in cat_subschema.types
        assert "Mechanism" in cat_subschema.types

    def test_filters_invalid_seed_types(self, mock_graphql_schema):
        """Should skip seed types not in schema."""
        graph = type_graph.build_type_graph(mock_graphql_schema)
        cat_data = {
            "description": "Test",
            "types": ["Target", "NonExistentType"],
        }
        cat_subschema = subschema._build_category_subschema(
            "test",
            cat_data,
            graph,
            mock_graphql_schema,
            depth=0,
        )

        # Should include Target but not NonExistentType
        assert "Target" in cat_subschema.types
        assert "NonExistentType" not in cat_subschema.types

    def test_generates_valid_sdl(self, mock_graphql_schema, mock_categories):
        """SDL should contain type definitions."""
        graph = type_graph.build_type_graph(mock_graphql_schema)
        cat_subschema = subschema._build_category_subschema(
            "shared-types",
            mock_categories["shared-types"],
            graph,
            mock_graphql_schema,
            depth=0,
        )

        assert "type Pagination" in cat_subschema.sdl


class TestPrefetchCategorySubschemas:
    """Tests for prefetch_category_subschemas function."""

    @pytest.mark.asyncio
    async def test_caches_subschemas(self, clear_cache, mock_graphql_schema):
        """Should cache subschemas after prefetch."""
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()
            await subschema.prefetch_category_subschemas(depth=1)

        assert subschema._cached_subschemas is not None
        assert len(subschema._cached_subschemas.subschemas) > 0

    @pytest.mark.asyncio
    async def test_respects_depth_setting(self, clear_cache, mock_graphql_schema):
        """Should use provided depth setting."""
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()
            await subschema.prefetch_category_subschemas(depth=0)

        assert subschema._cached_subschemas is not None
        assert subschema._cached_subschemas.depth == 0


class TestGetCategorySubschemas:
    """Tests for get_category_subschemas function."""

    @pytest.mark.asyncio
    async def test_returns_cached_subschemas(self, clear_cache, mock_graphql_schema):
        """Should return cached subschemas."""
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()
            await subschema.prefetch_category_subschemas(depth=1)
            result = subschema.get_category_subschemas()

        assert result is subschema._cached_subschemas

    def test_raises_if_not_prefetched(self, clear_cache):
        """Should raise RuntimeError if not prefetched."""
        with pytest.raises(RuntimeError, match="not initialized"):
            subschema.get_category_subschemas()


class TestGetCategoriesForDocstring:
    """Tests for get_categories_for_docstring function."""

    def test_formats_categories(self):
        """Should format categories for docstring."""
        result = subschema.get_categories_for_docstring()

        assert "Available categories:" in result
        # Should contain at least one category with description
        assert " - " in result
