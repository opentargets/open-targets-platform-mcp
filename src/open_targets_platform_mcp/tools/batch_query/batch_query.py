"""Batch query execution tool for Open Targets GraphQL API."""

import asyncio
from typing import Annotated, Any

from pydantic import Field

from open_targets_platform_mcp.client.graphql import execute_graphql_query
from open_targets_platform_mcp.model.result import (
    BatchQueryResult,
    BatchQuerySingleResult,
    BatchQuerySummary,
    QueryResult,
    QueryResultStatus,
)


async def _handle_single_query(
    index: int,
    query_string: str,
    variables: dict[str, Any],
    key_field: str,
    jq_filter: str | None,
    semaphore: asyncio.Semaphore,
) -> BatchQuerySingleResult:
    async with semaphore:
        result: QueryResult | None = None
        key: str | None = None
        if key_field not in variables:
            key = None
            result = QueryResult.create_error(
                f"Key field '{key_field}' not found in variables at index {index}",
                variables=variables,
            )
        else:
            key = str(variables[key_field])
            result = await execute_graphql_query(query_string, variables, jq_filter=jq_filter)
            if result.status in (QueryResultStatus.ERROR, QueryResultStatus.WARNING):
                result = result.model_copy(update={"variables": variables})

        return BatchQuerySingleResult(index=index, key=key, result=result)


async def _batch_query_impl(
    query_string: str,
    variables_list: list[dict[str, Any]],
    key_field: str,
    jq_filter: str | None = None,
) -> BatchQueryResult | QueryResult:
    """Internal implementation - handles both jq-enabled and disabled modes."""
    if not variables_list:
        return QueryResult.create_error("variables_list cannot be empty")

    # serialising the execution for now before the GraphQL client cache is
    # implemented.
    semaphore = asyncio.Semaphore(1)
    tasks = [
        _handle_single_query(idx, query_string, variables, key_field, jq_filter, semaphore)
        for idx, variables in enumerate(variables_list)
    ]
    results = await asyncio.gather(*tasks)
    return BatchQueryResult(
        results=results,
        summary=BatchQuerySummary(
            total=len(variables_list),
            successful=len([result for result in results if result.result.status == QueryResultStatus.SUCCESS]),
            failed=len([result for result in results if result.result.status == QueryResultStatus.ERROR]),
            warning=len([result for result in results if result.result.status == QueryResultStatus.WARNING]),
        ),
    )


async def batch_query_with_jq(
    query_string: Annotated[
        str,
        Field(description="GraphQL query string"),
    ],
    variables_list: Annotated[
        list[dict[Any, Any]],
        Field(description="List of variables for each query execution"),
    ],
    key_field: Annotated[
        str,
        Field(description="Variable field to use as result key"),
    ],
    jq_filter: Annotated[
        str | None,
        Field(description="Optional jq filter applied to all results"),
    ] = None,
) -> BatchQueryResult | QueryResult:
    """Batch query with jq support - signature includes jq_filter."""
    return await _batch_query_impl(query_string, variables_list, key_field, jq_filter)


async def batch_query_without_jq(
    query_string: Annotated[
        str,
        Field(description="GraphQL query string"),
    ],
    variables_list: Annotated[
        list[dict[Any, Any]],
        Field(description="List of variables for each query execution"),
    ],
    key_field: Annotated[
        str,
        Field(description="Variable field to use as result key"),
    ],
) -> BatchQueryResult | QueryResult:
    """Batch query without jq support - signature excludes jq_filter."""
    return await _batch_query_impl(query_string, variables_list, key_field, None)
