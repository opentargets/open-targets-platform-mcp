from typing import Any, cast

import jq
from gql import Client, GraphQLRequest
from gql.client import AsyncClientSession
from gql.transport.aiohttp import AIOHTTPTransport
from graphql import GraphQLSchema

from open_targets_platform_mcp import __dist_name__, __version__
from open_targets_platform_mcp.model.exception import JqCompilationError
from open_targets_platform_mcp.model.query_result import QueryResult
from open_targets_platform_mcp.settings import settings


class _RuntimeState:
    client: Client | None = None
    session: AsyncClientSession | None = None


_runtime_state: _RuntimeState = _RuntimeState()


def _create_graphql_client(*, fetch_schema_from_transport: bool = False) -> Client:
    user_agent = f"{__dist_name__}/{__version__}"
    if settings.http_base_url:
        user_agent += f" ({settings.http_base_url})"
    transport = AIOHTTPTransport(
        url=str(settings.api_endpoint),
        headers={
            "Content-Type": "application/json",
            "User-Agent": user_agent,
        },
        timeout=settings.api_call_timeout,
    )
    return Client(transport=transport, fetch_schema_from_transport=fetch_schema_from_transport)


async def _get_global_graphql_session() -> AsyncClientSession:
    if _runtime_state.session is None:
        client = _create_graphql_client()
        connected_session = await client.connect_async()  # pyright: ignore[reportUnknownMemberType]
        _runtime_state.client = client
        _runtime_state.session = cast("AsyncClientSession", connected_session)

    return _runtime_state.session


def _compile_jq_filter(jq_filter: str | None) -> object | None:
    if jq_filter is None:
        return None

    try:
        return cast("Any", jq.compile(jq_filter))  # pyright: ignore[reportUnknownMemberType]
    except Exception as e:
        raise JqCompilationError(e) from e


def _apply_optional_filter(
    result: object,
    compiled_filter: object | None,
    jq_filter: str | None,
) -> QueryResult:
    if compiled_filter:
        try:
            filter_program = cast("Any", compiled_filter)
            filtered_results = cast("list[Any]", filter_program.input_value(result).all())
            return QueryResult.create_success(filtered_results)
        except Exception as jq_error:  # noqa: BLE001
            return QueryResult.create_warning(
                result,
                f"jq filter failed: {jq_error!s}. "
                "Tip: Use '// empty' or '// []' to handle null values. "
                f"Example: '{jq_filter} // empty'",
            )
    else:
        return QueryResult.create_success(result)


async def execute_graphql_query(
    query_string: str,
    variables: dict[str, Any] | None = None,
    jq_filter: str | None = None,
) -> QueryResult:
    """Make a generic GraphQL API call and apply a jq filter to the result."""
    try:
        session = await _get_global_graphql_session()
        request = GraphQLRequest(query_string, variable_values=variables)
        compiled_filter = _compile_jq_filter(jq_filter)
        result = await session.execute(request)
        result = _apply_optional_filter(result, compiled_filter, jq_filter)
    except Exception as exception:
        result = QueryResult.create_error(
            str(exception),
            error_type=type(exception).__name__,
        )
    return result


async def fetch_graphql_schema() -> GraphQLSchema:
    """Fetch the GraphQL schema from the configured endpoint URL."""
    # Create a client with schema fetching enabled.
    client = _create_graphql_client(fetch_schema_from_transport=True)

    async with client:
        # The schema is automatically fetched and stored in the client
        if not client.schema:
            error_msg = "Failed to fetch schema from the GraphQL endpoint."
            raise ValueError(error_msg)

        # Convert schema to SDL format
        return client.schema
