"""Tool for fetching the Open Targets Platform GraphQL schema."""

from graphql import print_schema

from open_targets_platform_mcp.client.graphql import fetch_graphql_schema

# Module-level cache for schema (pre-fetched at startup)
_cached_schema: str | None = None


async def prefetch_schema() -> None:
    """Pre-fetch and cache the GraphQL schema at server startup.

    This function should be called once during server initialization
    to ensure the schema is available immediately when requested.
    """
    global _cached_schema
    schema_obj = await fetch_graphql_schema()
    _cached_schema = print_schema(schema_obj)


async def get_open_targets_graphql_schema() -> str:
    """Retrieve the Open Targets Platform GraphQL schema.

    Returns the pre-fetched schema that was loaded at server startup.

    Returns:
        str: the schema text in SDL (Schema Definition Language) format.

    Raises:
        RuntimeError: If schema was not pre-fetched at startup.
    """
    if _cached_schema is None:
        raise RuntimeError("Schema not initialized. Call prefetch_schema() at server startup.")
    return _cached_schema
