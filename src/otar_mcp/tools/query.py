"""Tool for executing GraphQL queries against the OpenTargets API."""

import json
from typing import Annotated, Optional, Union

from pydantic import Field

from otar_mcp.client import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


@mcp.tool()
def query_open_targets_graphql(
    query_string: Annotated[str, Field(description="GraphQL query string starting with 'query' keyword")],
    variables: Annotated[
        Optional[Union[dict, str]],
        Field(description="Optional variables for the GraphQL query"),
    ] = None,
    jq_filter: Annotated[
        Optional[str],
        Field(description="Optional jq filter to pre-filter the JSON response server-side"),
    ] = None,
) -> dict:
    """Execute GraphQL queries against the Open Targets API.

    Returns:
        dict: GraphQL response with data field containing targets, diseases, drugs, variants, studies or error message.
    """
    try:
        # Parse variables if provided as a JSON string
        parsed_variables: Optional[dict] = variables if isinstance(variables, dict) else None
        if isinstance(variables, str):
            try:
                parsed_variables = json.loads(variables)
            except json.JSONDecodeError as e:
                return {"error": f"Failed to parse variables JSON string: {e!s}"}

        return execute_graphql_query(config.api_endpoint, query_string, parsed_variables, jq_filter=jq_filter)
    except Exception as e:
        return {"error": f"Failed to execute GraphQL query: {e!s}"}
