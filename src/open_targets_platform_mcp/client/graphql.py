from typing import Any, cast

import jq
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from graphql import GraphQLSchema

from open_targets_platform_mcp.model.result import QueryResult
from open_targets_platform_mcp.settings import settings


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
        QueryResult: The result of the GraphQL query
    """
    # Compile both the query and the jq filter before submitting a HTTP request
    # to detect errors early.
    query = gql(query_string)
    compiled_filter = None if jq_filter is None else cast("Any", jq.compile(jq_filter))  # pyright: ignore[reportUnknownMemberType]

    transport = AIOHTTPTransport(
        url=str(settings.api_endpoint),
        headers={
            "Content-Type": "application/json",
        },
        timeout=settings.api_call_timeout,
    )
    client = Client(transport=transport)
    result = await client.execute_async(query, variable_values=variables)

    if compiled_filter:
        try:
            filtered_results = cast("list[Any]", compiled_filter.input_value(result).all())
            return QueryResult.create_success(filtered_results)
        except Exception as jq_error:
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
