"""Tool for executing GraphQL queries against the OpenTargets API."""

from typing import Annotated, Any

from pydantic import Field

from open_targets_platform_mcp.client import execute_graphql_query
from open_targets_platform_mcp.model.result import QueryResult


async def _query_impl(
    query_string: str,
    variables: dict[str, Any] | None = None,
    jq_filter: str | None = None,
) -> QueryResult:
    return await execute_graphql_query(
        query_string,
        variables,
        jq_filter=jq_filter,
    )


async def query_with_jq(
    query_string: Annotated[
        str,
        Field(description="GraphQL query string starting with 'query' keyword"),
    ],
    variables: Annotated[
        dict[str, Any] | None,
        Field(description="Optional variables for the GraphQL query"),
    ] = None,
    jq_filter: Annotated[
        str | None,
        Field(description="Optional jq filter to pre-filter the JSON response server-side"),
    ] = None,
) -> QueryResult:
    """Query with jq support - signature includes jq_filter."""
    return await _query_impl(query_string, variables, jq_filter)


async def query_without_jq(
    query_string: Annotated[
        str,
        Field(description="GraphQL query string starting with 'query' keyword"),
    ],
    variables: Annotated[
        dict[str, Any] | None,
        Field(description="Optional variables for the GraphQL query"),
    ] = None,
) -> QueryResult:
    """Query without jq support - signature excludes jq_filter."""
    return await _query_impl(query_string, variables)
