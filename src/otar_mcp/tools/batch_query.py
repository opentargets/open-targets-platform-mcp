"""Batch query execution tool for Open Targets GraphQL API."""

from typing import Annotated, Optional

from pydantic import Field

from otar_mcp.client.graphql import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


@mcp.tool()
def batch_query_open_targets_graphql(
    query_string: Annotated[str, Field(description="GraphQL query string")],
    variables_list: Annotated[list[dict], Field(description="List of variables for each query execution")],
    key_field: Annotated[str, Field(description="Variable field to use as result key")],
    jq_filter: Annotated[Optional[str], Field(description="Optional jq filter applied to all results")] = None,
) -> dict:
    """Execute the same GraphQL query multiple times with different variable sets.

    Use this tool instead of the regular query tool when you need to run the same query
    repeatedly with different arguments (e.g., querying multiple drugs, targets, or diseases).

    Args:
        query_string: The GraphQL query string to execute for all variable sets
        variables_list: List of variable dictionaries, one per query execution
        key_field: Variable field name to use as key in results mapping (e.g., "chemblId")
        jq_filter: Optional jq filter applied identically and individually to all query results

    Returns:
        dict: Results keyed by the specified field value, with execution summary:
            {
                "status": "success",
                "results": {
                    "<key_value>": {"status": "success", "data": ...},
                    ...
                },
                "summary": {"total": <int>, "successful": <int>, "failed": <int>}
            }
    """
    try:
        # Validate that variables_list is not empty
        if not variables_list:
            return {"error": "variables_list cannot be empty"}

        # Initialize results structure
        results = {}
        successful_count = 0
        failed_count = 0
        total_count = len(variables_list)

        # Execute queries sequentially
        # TODO: Add parallel execution support for better performance
        for idx, variables in enumerate(variables_list):
            # Extract the key value for this query
            if key_field not in variables:
                key_value = f"query_{idx}"  # Fallback to index if key_field not found
                result_entry = {
                    "status": "error",
                    "message": f"Key field '{key_field}' not found in variables at index {idx}",
                    "variables": variables,
                }
                results[key_value] = result_entry
                failed_count += 1
                continue

            key_value = str(variables[key_field])

            try:
                # Execute the GraphQL query (jq filter applied inside execute_graphql_query)
                response = execute_graphql_query(
                    endpoint_url=config.api_endpoint,
                    query_string=query_string,
                    variables=variables,
                    jq_filter=jq_filter,
                )

                # Check if the query execution itself failed
                if response.get("status") == "error":
                    results[key_value] = response
                    failed_count += 1
                    continue

                # Store successful result (may include warning if jq filter failed)
                results[key_value] = response
                successful_count += 1

            except Exception as query_error:
                # Catch any other exceptions during query execution
                results[key_value] = {
                    "status": "error",
                    "message": f"Query execution failed: {query_error!s}",
                    "variables": variables,
                }
                failed_count += 1

    except Exception as e:
        return {"error": f"Batch query execution failed: {e!s}"}
    else:
        # Return batch results with summary
        return {
            "status": "success",
            "results": results,
            "summary": {
                "total": total_count,
                "successful": successful_count,
                "failed": failed_count,
            },
        }
