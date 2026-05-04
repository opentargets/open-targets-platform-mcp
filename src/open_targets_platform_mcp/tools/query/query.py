"""Tool for executing GraphQL queries against the Open Targets Platform API."""

from typing import Annotated, Any

from open_targets_platform_mcp.client import execute_graphql_query
from open_targets_platform_mcp.model.query_result import QueryResult
from open_targets_platform_mcp.tools.helper import clone_function_with_removed_parameter


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
        "GraphQL query string starting with 'query' keyword.",
    ],
    variables: Annotated[
        dict[str, Any] | None,
        "Optional dict or JSON string with query variables.",
    ] = None,
    jq_filter: Annotated[
        str | None,
        "Optional jq filter to pre-filter the JSON response server-side. "
        "Always use null coalescing (`//`) to handle null or missing values gracefully, "
        'for example: `// empty`, `// []`, `// {}`, `// ""`, or any other sensible default.',
    ] = None,
) -> Annotated[
    QueryResult,
    "GraphQL response with data field containing targets, diseases, drugs, variants, studies or error message.",
]:
    return await _query_impl(query_string, variables, jq_filter)


query_without_jq = clone_function_with_removed_parameter(query_with_jq, "jq_filter")
