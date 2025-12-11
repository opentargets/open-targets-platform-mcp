"""Tool for fetching the OpenTargets GraphQL schema."""

import asyncio
import time
from typing import Any

from graphql import print_schema

from open_targets_platform_mcp.client.graphql import fetch_graphql_schema

# Cache TTL: 1 hour in seconds
_SCHEMA_CACHE_TTL = 3600

# Module-level cache for schema
_cache: dict[str, Any] = {}
_cache_lock = asyncio.Lock()


async def get_open_targets_graphql_schema() -> str:
    """Retrieve the Open Targets Platform GraphQL schema.

    Fetches the latest schema dynamically from the API using
    the gql client's built-in schema fetching. Results are cached
    for 1 hour to reduce API calls.

    Returns:
        str: the schema text in SDL (Schema Definition Language) format.
    """
    current_time = time.time()

    # Check cache with lock to prevent concurrent fetches
    async with _cache_lock:
        # Check if we have a valid cached schema
        if "schema" in _cache and "timestamp" in _cache and (current_time - _cache["timestamp"]) < _SCHEMA_CACHE_TTL:
            return _cache["schema"]

        # Cache miss or expired - fetch new schema
        schema_obj = await fetch_graphql_schema()

        # Convert to SDL string format
        schema_sdl = print_schema(schema_obj)

        # Update cache with string
        _cache["schema"] = schema_sdl
        _cache["timestamp"] = current_time

        return schema_sdl
