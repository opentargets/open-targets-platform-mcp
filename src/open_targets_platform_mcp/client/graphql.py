from collections.abc import Sequence
from typing import Any, cast

import jq
from gql import Client, GraphQLRequest, gql
from gql.client import AsyncClientSession
from gql.transport.aiohttp import AIOHTTPTransport
from graphql import GraphQLSchema

from open_targets_platform_mcp.model.result import QueryResult
from open_targets_platform_mcp.settings import settings


class _RuntimeState:
    client: Client | None = None
    session: AsyncClientSession | None = None


_runtime_state: _RuntimeState = _RuntimeState()


def _create_graphql_client(*, fetch_schema_from_transport: bool = False) -> Client:
    transport = AIOHTTPTransport(
        url=str(settings.api_endpoint),
        headers={
            "Content-Type": "application/json",
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
    return None if jq_filter is None else cast("Any", jq.compile(jq_filter))  # pyright: ignore[reportUnknownMemberType]


def _result_with_optional_filter(
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

    return QueryResult.create_success(result)


async def _execute_graphql_query_with_session(
    session: AsyncClientSession,
    query_string: str,
    variables: dict[str, Any] | None = None,
    jq_filter: str | None = None,
) -> QueryResult:
    query = gql(query_string)
    compiled_filter = _compile_jq_filter(jq_filter)
    request = GraphQLRequest(query, variable_values=variables)
    result = await session.execute(request)

    return _result_with_optional_filter(result, compiled_filter, jq_filter)


async def _execute_graphql_batch_query_with_session(
    session: AsyncClientSession,
    query_string: str,
    variables_list: Sequence[dict[str, Any]],
    jq_filter: str | None = None,
) -> list[QueryResult]:
    query = gql(query_string)
    compiled_filter = _compile_jq_filter(jq_filter)
    requests = [GraphQLRequest(query, variable_values=variables) for variables in variables_list]
    raw_results = await session.execute_batch(requests)

    return [_result_with_optional_filter(result, compiled_filter, jq_filter) for result in raw_results]


async def execute_graphql_query(
    query_string: str,
    variables: dict[str, Any] | None = None,
    jq_filter: str | None = None,
) -> QueryResult:
    """Make a generic GraphQL API call and apply a jq filter to the result."""
    session = await _get_global_graphql_session()
    return await _execute_graphql_query_with_session(session, query_string, variables, jq_filter)


async def execute_graphql_batch_query(
    query_string: str,
    variables_list: Sequence[dict[str, Any]],
    jq_filter: str | None = None,
) -> list[QueryResult]:
    """Execute one query with many variable sets, one result per set."""
    session = await _get_global_graphql_session()
    return await _execute_graphql_batch_query_with_session(session, query_string, variables_list, jq_filter)


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
