"""Batch query execution tool for Open Targets Platform GraphQL API."""

from typing import Annotated, Any

from pydantic import Field

from open_targets_platform_mcp.client.graphql import execute_graphql_batch_query
from open_targets_platform_mcp.model.result import (
    BatchQueryResult,
    BatchQuerySingleResult,
    BatchQuerySummary,
    QueryResult,
    QueryResultStatus,
)


def _build_summary(results: list[BatchQuerySingleResult], total: int) -> BatchQuerySummary:
    return BatchQuerySummary(
        total=total,
        successful=len([result for result in results if result.result.status == QueryResultStatus.SUCCESS]),
        failed=len([result for result in results if result.result.status == QueryResultStatus.ERROR]),
        warning=len([result for result in results if result.result.status == QueryResultStatus.WARNING]),
    )


async def _batch_query_impl(
    query_string: str,
    variables_list: list[dict[str, Any]],
    key_field: str,
    jq_filter: str | None = None,
) -> BatchQueryResult | QueryResult:
    """Internal implementation - handles both jq-enabled and disabled modes."""
    if not variables_list:
        return QueryResult.create_error("variables_list cannot be empty")

    results: list[BatchQuerySingleResult] = []
    valid_indices: list[int] = []
    valid_variables_list: list[dict[str, Any]] = []

    for idx, variables in enumerate(variables_list):
        if key_field not in variables:
            results.append(
                BatchQuerySingleResult(
                    index=idx,
                    key=None,
                    result=QueryResult.create_error(
                        f"Key field '{key_field}' not found in variables at index {idx}",
                        variables=variables,
                    ),
                ),
            )
            continue

        valid_indices.append(idx)
        valid_variables_list.append(variables)

    if valid_variables_list:
        query_results = await execute_graphql_batch_query(query_string, valid_variables_list, jq_filter)

        for idx, variables, result_item in zip(valid_indices, valid_variables_list, query_results, strict=True):
            key = str(variables[key_field])
            processed_result = result_item
            if result_item.status in (QueryResultStatus.ERROR, QueryResultStatus.WARNING):
                processed_result = result_item.model_copy(update={"variables": variables})

            results.append(BatchQuerySingleResult(index=idx, key=key, result=processed_result))

    results.sort(key=lambda item: item.index)

    return BatchQueryResult(
        results=results,
        summary=_build_summary(results, len(variables_list)),
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
