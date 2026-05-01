"""Batch query execution tool for Open Targets Platform GraphQL API."""

import asyncio
from typing import Annotated, Any

from pydantic import Field

from open_targets_platform_mcp.client.graphql import execute_graphql_query
from open_targets_platform_mcp.model.query_result import (
    BatchQueryResult,
    BatchQueryResultItem,
    BatchQueryStatusCounts,
    QueryResult,
    QueryResultStatus,
)
from open_targets_platform_mcp.tools.helper import clone_function_with_removed_parameter


async def _handle_single_query(
    index: int,
    query_string: str,
    variables: dict[str, Any],
    key_field: str,
    jq_filter: str | None,
    semaphore: asyncio.Semaphore,
) -> BatchQueryResultItem:
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

        return BatchQueryResultItem(index=index, id=key, result=result)


async def _batch_query_impl(
    query_string: str,
    variables_list: list[dict[str, Any]],
    key_field: str,
    jq_filter: str | None = None,
) -> BatchQueryResult:
    """Internal implementation - handles both jq-enabled and disabled modes."""
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
        status_counts=BatchQueryStatusCounts(
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
        Field(
            description="List of variables for each query execution",
            min_length=1,
        ),
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


batch_query_without_jq = clone_function_with_removed_parameter(batch_query_with_jq, "jq_filter")
