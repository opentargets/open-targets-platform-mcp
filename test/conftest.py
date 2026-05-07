"""Shared pytest fixtures and the cassette-based gql session mock."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from graphql import build_schema

# ---------------------------------------------------------------------------
# --live flag
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run tests against the real GraphQL API instead of the cassette.",
    )


@pytest.fixture(scope="session")
def live(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--live"))


# ---------------------------------------------------------------------------
# Fixture file paths
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "generated"
CASSETTE_PATH = FIXTURES_DIR / "graphql_cassette.json"
SCHEMA_SDL_PATH = FIXTURES_DIR / "schema.graphql"


# ---------------------------------------------------------------------------
# Cassette helpers
# ---------------------------------------------------------------------------


def _normalize(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip())


def _load_cassette() -> list[dict]:
    with CASSETTE_PATH.open() as f:
        return json.load(f)["records"]


def _cassette_lookup(cassette: list[dict], query: str, variables: dict | None) -> dict:
    """Return the recorded response for the given query + variables pair.

    Raises KeyError if no matching entry is found.
    """
    norm = _normalize(query)
    for entry in cassette:
        if _normalize(entry["request"]["query"]) == norm and entry["request"]["variables"] == variables:
            return entry["response"]
    raise KeyError(
        f"No cassette entry for query={norm!r} variables={variables!r}",
    )


# ---------------------------------------------------------------------------
# Low-level gql session mock
# ---------------------------------------------------------------------------


class CassetteSession:
    """Async mock that replays responses from the cassette JSON file."""

    def __init__(self, cassette: list[dict]) -> None:
        self._cassette = cassette

    async def execute(self, request: Any) -> dict:  # noqa: ANN401
        from gql import GraphQLRequest
        from gql.transport.exceptions import TransportQueryError
        from graphql import print_ast

        if isinstance(request, GraphQLRequest):
            query_str = print_ast(request.document)
            variables = request.variable_values or None
        else:
            query_str = str(request)
            variables = None

        response = _cassette_lookup(self._cassette, query_str, variables)
        if "_error" in response:
            import gql.transport.exceptions as _gql_exc

            exc_cls = getattr(_gql_exc, response.get("_error_type", ""), TransportQueryError)
            if not (isinstance(exc_cls, type) and issubclass(exc_cls, Exception)):
                exc_cls = TransportQueryError
            raise exc_cls(response["_error"])
        return response


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cassette() -> list[dict]:
    return _load_cassette()


@pytest.fixture
def graphql_schema():
    """Return a real GraphQLSchema object built from the captured SDL."""
    sdl = SCHEMA_SDL_PATH.read_text(encoding="utf-8")
    return build_schema(sdl)


@pytest.fixture(autouse=True)
def reset_graphql_runtime():
    """Reset the global gql session between tests so mocks don't bleed."""
    import open_targets_platform_mcp.client.graphql as gql_module

    gql_module._runtime_state.session = None
    gql_module._runtime_state.client = None
    yield
    gql_module._runtime_state.session = None
    gql_module._runtime_state.client = None


@pytest.fixture
def mock_gql_session(live, cassette):
    """Patch _get_global_graphql_session to return a CassetteSession.

    When --live is passed the patch is skipped and the real session is used.
    """
    if live:
        yield None
        return

    session = CassetteSession(cassette)
    with patch(
        "open_targets_platform_mcp.client.graphql._get_global_graphql_session",
        new=AsyncMock(return_value=session),
    ):
        yield session


@pytest.fixture
def mock_schema_caches(live, graphql_schema):
    """Pre-populate schema, type_graph, and category_subschemas caches.

    When --live is passed the caches are left empty so they fetch from the
    real API on first access (the normal production path).
    """
    if live:
        yield
        return

    from open_targets_platform_mcp.settings import settings
    from open_targets_platform_mcp.tools.schema import caches
    from open_targets_platform_mcp.tools.schema.helper import build_type_graph, load_categories
    from open_targets_platform_mcp.tools.schema.helper.subschema import (
        CategorySubschema,
        CategorySubschemas,
        build_category_subschema,
    )

    graph = build_type_graph(graphql_schema)
    categories = load_categories()
    depth = settings.subschema_depth

    subschemas: dict[str, CategorySubschema] = {}
    for name, data in categories.items():
        subschemas[name] = build_category_subschema(name, data, graph, graphql_schema, depth)

    caches.schema_cache.set(graphql_schema)
    caches.type_graph_cache.set(graph)
    caches.category_subschemas_cache.set(CategorySubschemas(subschemas=subschemas, depth=depth))

    yield

    caches.schema_cache.clear()
    caches.type_graph_cache.clear()
    caches.category_subschemas_cache.clear()


@pytest.fixture
async def mcp_client_no_jq(mock_gql_session, mock_schema_caches):
    """Open an in-process fastmcp Client with all mocks active.

    Depends on both mock_gql_session and mock_schema_caches so that all tool
    categories work correctly.  In live mode both mocks are no-ops.
    """
    from fastmcp import Client

    from open_targets_platform_mcp.create_server import create_server

    server = await create_server()
    async with Client(server) as client:
        yield client


@pytest.fixture
async def mcp_client_jq(mock_gql_session, mock_schema_caches):
    """Like mcp_client but with jq_enabled=True.

    Used to test jq-specific tool behaviour through the MCP protocol.
    """
    from fastmcp import Client

    from open_targets_platform_mcp.create_server import create_server
    from open_targets_platform_mcp.settings import settings

    settings.jq_enabled = True
    try:
        server = await create_server()
        async with Client(server) as client:
            yield client
    finally:
        settings.jq_enabled = False
