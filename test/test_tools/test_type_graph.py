"""Tests for type graph module."""

from unittest.mock import AsyncMock, patch

import pytest
from graphql import build_schema

from open_targets_platform_mcp.tools.schema import type_graph


@pytest.fixture
def clear_cache():
    """Clear the type graph cache before and after each test."""
    type_graph._cached_type_graph = None
    type_graph._cached_schema = None
    yield
    type_graph._cached_type_graph = None
    type_graph._cached_schema = None


@pytest.fixture
def mock_graphql_schema():
    """Create a mock GraphQL schema for testing."""
    return build_schema(
        """
        type Query {
            target(ensemblId: String!): Target
            disease(efoId: String!): Disease
        }

        \"\"\"A target entity representing a gene or protein\"\"\"
        type Target {
            id: String!
            approvedSymbol: String
            diseases: [Disease!]
            pathways: [Pathway!]
        }

        \"\"\"A disease entity\"\"\"
        type Disease {
            id: String!
            name: String
            targets: [Target!]
            drugs: [Drug!]
        }

        \"\"\"A drug/molecule entity\"\"\"
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

        enum DiseaseType {
            RARE
            COMMON
        }

        union SearchResult = Target | Disease | Drug
        """,
    )


class TestIsCustomType:
    """Tests for _is_custom_type function."""

    def test_custom_type_returns_true(self):
        assert type_graph._is_custom_type("Target") is True
        assert type_graph._is_custom_type("Disease") is True
        assert type_graph._is_custom_type("MyCustomType") is True

    def test_builtin_scalar_returns_false(self):
        assert type_graph._is_custom_type("String") is False
        assert type_graph._is_custom_type("Int") is False
        assert type_graph._is_custom_type("Float") is False
        assert type_graph._is_custom_type("Boolean") is False
        assert type_graph._is_custom_type("ID") is False

    def test_introspection_type_returns_false(self):
        assert type_graph._is_custom_type("__Schema") is False
        assert type_graph._is_custom_type("__Type") is False
        assert type_graph._is_custom_type("__Field") is False


class TestGetTypeCategory:
    """Tests for _get_type_category function."""

    def test_object_type(self, mock_graphql_schema):
        target_type = mock_graphql_schema.type_map["Target"]
        assert type_graph._get_type_category(target_type) == "object"

    def test_enum_type(self, mock_graphql_schema):
        enum_type = mock_graphql_schema.type_map["DiseaseType"]
        assert type_graph._get_type_category(enum_type) == "enum"

    def test_union_type(self, mock_graphql_schema):
        union_type = mock_graphql_schema.type_map["SearchResult"]
        assert type_graph._get_type_category(union_type) == "union"


class TestBuildTypeGraph:
    """Tests for build_type_graph function."""

    def test_builds_adjacency_for_object_types(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)

        # Target should reference Disease and Pathway
        assert "Disease" in graph.adjacency["Target"]
        assert "Pathway" in graph.adjacency["Target"]

        # Disease should reference Target and Drug
        assert "Target" in graph.adjacency["Disease"]
        assert "Drug" in graph.adjacency["Disease"]

    def test_captures_field_names(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)

        # Check field names are captured
        assert "diseases" in graph.adjacency["Target"]["Disease"]
        assert "pathways" in graph.adjacency["Target"]["Pathway"]

    def test_filters_introspection_types(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)

        # Introspection types should not be in the graph
        assert "__Schema" not in graph.types
        assert "__Type" not in graph.types

    def test_filters_builtin_scalars(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)

        # Built-in scalars should not be in adjacency values
        for type_name, refs in graph.adjacency.items():
            assert "String" not in refs
            assert "Int" not in refs

    def test_builds_reverse_adjacency(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)

        # Disease is referenced by Target
        assert "Target" in graph.reverse_adjacency["Disease"]
        # Target is referenced by Disease
        assert "Disease" in graph.reverse_adjacency["Target"]

    def test_handles_union_types(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)

        # SearchResult union should reference its member types
        assert "Target" in graph.adjacency["SearchResult"]
        assert "Disease" in graph.adjacency["SearchResult"]
        assert "Drug" in graph.adjacency["SearchResult"]

    def test_stores_type_metadata(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)

        assert graph.types["Target"] == "object"
        assert graph.types["DiseaseType"] == "enum"
        assert graph.types["SearchResult"] == "union"


class TestGetReachableTypes:
    """Tests for _get_reachable_types function."""

    def test_returns_start_type(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)
        reachable = type_graph._get_reachable_types(graph, "Pathway")

        assert "Pathway" in reachable

    def test_finds_direct_dependencies(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)
        reachable = type_graph._get_reachable_types(graph, "Target")

        assert "Disease" in reachable
        assert "Pathway" in reachable

    def test_finds_transitive_dependencies(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)
        reachable = type_graph._get_reachable_types(graph, "Target")

        # Target -> Disease -> Drug -> Mechanism
        assert "Drug" in reachable
        assert "Mechanism" in reachable

    def test_handles_cycles(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)
        # Target <-> Disease is a cycle
        reachable = type_graph._get_reachable_types(graph, "Target")

        # Should not infinite loop, should contain both
        assert "Target" in reachable
        assert "Disease" in reachable

    def test_leaf_type_returns_only_self(self, mock_graphql_schema):
        graph = type_graph.build_type_graph(mock_graphql_schema)
        reachable = type_graph._get_reachable_types(graph, "Mechanism")

        # Mechanism has no outgoing references
        assert reachable == {"Mechanism"}


class TestPrefetchTypeGraph:
    """Tests for prefetch_type_graph function."""

    @pytest.mark.asyncio
    async def test_caches_type_graph(self, clear_cache, mock_graphql_schema):
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()

        assert type_graph._cached_type_graph is not None
        assert type_graph._cached_schema is not None
        assert "Target" in type_graph._cached_type_graph.types

    @pytest.mark.asyncio
    async def test_get_type_graph_returns_cached(self, clear_cache, mock_graphql_schema):
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()
            graph = type_graph.get_type_graph()

        assert graph is type_graph._cached_type_graph


class TestGetTypeDependencies:
    """Tests for get_type_dependencies MCP tool."""

    @pytest.mark.asyncio
    async def test_single_type_returns_all_deps(self, clear_cache, mock_graphql_schema):
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()
            result = await type_graph.get_type_dependencies(["Target"])

        # Should return dict
        assert isinstance(result, dict)
        assert "Target" in result
        assert "shared" in result
        # Single type: all deps go under the type key, shared is empty
        all_sdl = result["Target"] + result["shared"]
        assert "type Target" in all_sdl
        assert "type Disease" in all_sdl
        assert "type Drug" in all_sdl
        assert "type Pathway" in all_sdl
        assert "type Mechanism" in all_sdl

    @pytest.mark.asyncio
    async def test_includes_descriptions(self, clear_cache, mock_graphql_schema):
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()
            result = await type_graph.get_type_dependencies(["Target"])

        # Should include type descriptions
        all_sdl = result["Target"] + result["shared"]
        assert "A target entity representing a gene or protein" in all_sdl

    @pytest.mark.asyncio
    async def test_multiple_types_separates_shared(self, clear_cache, mock_graphql_schema):
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()
            # Target and Disease share some dependencies
            result = await type_graph.get_type_dependencies(["Target", "Disease"])

        assert "Target" in result
        assert "Disease" in result
        assert "shared" in result
        # Shared types should be in shared, not duplicated
        # Target and Disease both reach Drug, so Drug should be in shared
        assert "type Drug" in result["shared"]

    @pytest.mark.asyncio
    async def test_raises_for_invalid_type(self, clear_cache, mock_graphql_schema):
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()

            with pytest.raises(ValueError, match="not found in schema"):
                await type_graph.get_type_dependencies(["NonExistentType"])

    @pytest.mark.asyncio
    async def test_suggests_similar_types(self, clear_cache, mock_graphql_schema):
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()

            with pytest.raises(ValueError, match="Target"):
                await type_graph.get_type_dependencies(["target"])  # lowercase

    @pytest.mark.asyncio
    async def test_raises_if_not_prefetched(self, clear_cache):
        with pytest.raises(RuntimeError, match="not initialized"):
            await type_graph.get_type_dependencies(["Target"])

    @pytest.mark.asyncio
    async def test_leaf_type_returns_only_self(self, clear_cache, mock_graphql_schema):
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()
            result = await type_graph.get_type_dependencies(["Mechanism"])

        # Should only contain Mechanism
        all_sdl = result["Mechanism"] + result["shared"]
        assert "type Mechanism" in all_sdl
        # Should not contain other types
        assert "type Target" not in all_sdl
        assert "type Disease" not in all_sdl

    @pytest.mark.asyncio
    async def test_disjoint_types_no_shared(self, clear_cache, mock_graphql_schema):
        with patch(
            "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_graphql_schema

            await type_graph.prefetch_type_graph()
            # Pathway and Mechanism have no shared dependencies
            result = await type_graph.get_type_dependencies(["Pathway", "Mechanism"])

        # Each should have only itself, no shared
        assert "type Pathway" in result["Pathway"]
        assert "type Mechanism" in result["Mechanism"]
        assert result["shared"] == ""
