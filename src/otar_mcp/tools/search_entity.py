"""Tool for executing entity search queries."""

from typing import Annotated

from pydantic import Field

from otar_mcp.client import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp

# GraphQL query for entity search - baked in directly
SEARCH_ENTITY_QUERY = """
query searchEntity($queryString: String!) {
  search(queryString: $queryString) {
    total
    hits {
      id
      entity
      description
    }
  }
}
"""


@mcp.tool(name="search_entity")
def search_entity(
    query_strings: Annotated[
        list[str],
        Field(
            description="List of search query strings to find entities (e.g., ['BRCA1', 'breast cancer', 'aspirin'])"
        ),
    ],
) -> dict:
    """Search for entities across multiple types using the Open Targets search API.

    This tool performs a streamlined entity search that returns the id and entity type
    for up to 3 matching entities across targets, diseases, drugs, variants, and studies.

    Supports multiple query strings in a single call - each query is executed independently
    and results are returned in a dictionary keyed by the query string.

    Args:
        query_strings: List of search queries (e.g., ["BRCA1", "breast cancer", "aspirin"])

    Returns:
        dict: Dictionary mapping each query string to its results (array of up to 3 entities
              with id and entity fields), or error message if any query fails.

    Example:
        Input: ["BRCA1", "aspirin"]
        Output: {
            "BRCA1": [
                {"id": "ENSG00000012048", "entity": "target"},
                {"id": "EFO_0000305", "entity": "disease"}
            ],
            "aspirin": [
                {"id": "CHEMBL25", "entity": "drug"}
            ]
        }
    """
    # Hardcoded jq filter to return only id and entity from first 3 results
    jq_filter = ".data.search.hits[:3] | map({id, entity})"

    # Execute query for each search string
    results = {}
    for query_string in query_strings:
        variables = {
            "queryString": query_string,
        }

        try:
            result = execute_graphql_query(
                config.api_endpoint,
                SEARCH_ENTITY_QUERY,
                variables,
                jq_filter=jq_filter,
            )
        except Exception as e:
            return {"error": f"Failed to execute search query: {e!s}"}

        # Store result keyed by query string
        # If there's an error, the whole result will be an error dict
        if isinstance(result, dict) and "error" in result:
            return result

        results[query_string] = result

    return results
