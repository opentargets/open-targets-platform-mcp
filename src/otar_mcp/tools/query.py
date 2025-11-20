"""Tool for executing GraphQL queries against the OpenTargets API."""

import json
from typing import Annotated, Optional, Union

from pydantic import Field

from otar_mcp.client import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


@mcp.tool(name="query_open_targets_graphql")
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

    IMPORTANT: Before writing any query, you MUST first call the `get_open_targets_query_examples`
    tool with relevant categories (e.g., ["target", "disease", "drug"]) to learn the proper
    query syntax, available fields, required variables, and structure. Use the examples as
    templates for constructing your queries.

    ALWAYS use a jq filter to return ONLY the specific information requested by the user.
    This achieves parsimony by reducing token consumption and response size. Never return
    the full API response when only specific fields are needed.

    Args:
        query_string: GraphQL query starting with 'query' keyword
        variables: Optional dict or JSON string with query variables
        jq_filter: Optional jq expression to filter the response server-side

    Returns:
        dict: GraphQL response with data field containing targets, diseases, drugs, variants,
              studies or error message.
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
