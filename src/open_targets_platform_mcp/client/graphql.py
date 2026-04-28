import asyncio
from typing import Any, cast

import jq
from fastmcp.exceptions import ToolError
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import (
    TransportConnectionFailed,
    TransportProtocolError,
    TransportQueryError,
    TransportServerError,
)
from graphql import GraphQLSchema
from graphql.error import GraphQLError

from open_targets_platform_mcp.client.error_hints import build_hints, render_error_with_hints
from open_targets_platform_mcp.model.result import QueryResult
from open_targets_platform_mcp.settings import settings

_SCHEMA_FETCH_TIMEOUT_CAP = 10


async def _get_cached_schema_safe() -> GraphQLSchema | None:
    """Best-effort fetch of the cached parsed schema for hint enrichment.

    Reuses `tools.schema.caches.schema_cache` (lazy import to break the
    import cycle: that module imports `fetch_graphql_schema` from here).
    Never raises; returns `None` on any failure or timeout so error responses
    can still ship with regex-derived hints when introspection is unavailable.
    """
    try:
        from open_targets_platform_mcp.tools.schema.caches import schema_cache

        timeout = min(int(settings.api_call_timeout), _SCHEMA_FETCH_TIMEOUT_CAP)
        return await asyncio.wait_for(schema_cache.get(), timeout=timeout)
    except Exception:
        return None


async def execute_graphql_query(
    query_string: str,
    variables: dict[str, Any] | None = None,
    jq_filter: str | None = None,
) -> QueryResult:
    """Make a generic GraphQL API call and apply a jq filter to the result.

    Args:
        query_string (str): The GraphQL query or mutation as a string
        variables (dict, optional): Variables for the GraphQL query
        jq_filter (str, optional): jq filter to apply to the result

    Returns:
        QueryResult: A success (`QueryResultStatus.SUCCESS`) carrying the
            (optionally jq-filtered) GraphQL response, or a warning
            (`QueryResultStatus.WARNING`) when the GraphQL call succeeded
            but the jq filter failed at runtime.

    Raises:
        ToolError: For every recognised pre-call or transport-level failure,
            i.e. GraphQL syntax errors from `gql()`, jq-filter compile errors
            from `jq.compile`, and `gql.transport.exceptions.Transport*` /
            `asyncio.TimeoutError` raised by the transport. The message is
            human-readable prose with did-you-mean hints derived from the
            live schema where applicable. `ToolError` is re-raised verbatim
            by FastMCP regardless of `mask_error_details`, so the message
            reaches MCP clients with `isError=true`.
    """
    # Compile both the query and the jq filter before submitting an HTTP
    # request so detectable errors surface before any network round-trip.
    try:
        query = gql(query_string)
    except GraphQLError as e:
        schema = await _get_cached_schema_safe()
        try:
            hints = build_hints([{"message": str(e)}], schema)
        except Exception:
            hints = []
        msg = render_error_with_hints("graphql_syntax_error", str(e), hints)
        raise ToolError(msg) from e
    try:
        compiled_filter = None if jq_filter is None else cast("Any", jq.compile(jq_filter))  # pyright: ignore[reportUnknownMemberType]
    except Exception as e:
        msg = render_error_with_hints("filter_compile_error", str(e))
        raise ToolError(msg) from e

    transport = AIOHTTPTransport(
        url=str(settings.api_endpoint),
        headers={
            "Content-Type": "application/json",
        },
        timeout=settings.api_call_timeout,
    )
    client = Client(transport=transport)
    try:
        result = await client.execute_async(query, variable_values=variables)
    except TransportQueryError as e:
        schema = await _get_cached_schema_safe()
        errors = e.errors or []
        msg = render_error_with_hints(
            "graphql_query_error",
            "Query failed against the Open Targets server.",
            build_hints(errors, schema),
        )
        raise ToolError(msg) from e
    except TransportServerError as e:
        msg = render_error_with_hints("server_error", str(e))
        raise ToolError(msg) from e
    except TransportProtocolError as e:
        msg = render_error_with_hints("protocol_error", str(e))
        raise ToolError(msg) from e
    except TransportConnectionFailed as e:
        msg = render_error_with_hints("connection_error", str(e))
        raise ToolError(msg) from e
    except asyncio.TimeoutError as e:
        msg = render_error_with_hints("timeout", str(e))
        raise ToolError(msg) from e

    if compiled_filter:
        try:
            filtered_results = cast("list[Any]", compiled_filter.input_value(result).all())
            return QueryResult.create_success(filtered_results)
        except Exception as jq_error:  # noqa: BLE001 - jq raises bare Exception subclasses
            return QueryResult.create_warning(
                result,
                f"jq filter failed: {jq_error!s}. "
                "Tip: Use '// empty' or '// []' to handle null values. "
                f"Example: '{jq_filter} // empty'",
            )
    return QueryResult.create_success(result)


async def fetch_graphql_schema() -> GraphQLSchema:
    """Fetch the GraphQL schema from the configured endpoint URL.

    Uses the gql client's built-in schema fetching capability to retrieve
    the schema automatically via introspection.

    Returns:
        str: The GraphQL schema in SDL (Schema Definition Language) format.

    Raises:
        ValueError: If the schema could not be fetched from the endpoint.
    """
    # Create a transport with the GraphQL endpoint
    transport = AIOHTTPTransport(
        url=str(settings.api_endpoint),
        headers={
            "Content-Type": "application/json",
        },
        timeout=settings.api_call_timeout,
    )

    # Create a client with schema fetching enabled
    client = Client(transport=transport, fetch_schema_from_transport=True)

    async with client:
        # The schema is automatically fetched and stored in the client
        if not client.schema:
            error_msg = "Failed to fetch schema from the GraphQL endpoint."
            raise ValueError(error_msg)

        # Convert schema to SDL format
        return client.schema
