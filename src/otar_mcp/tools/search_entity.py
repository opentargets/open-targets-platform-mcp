"""Tool for executing entity search queries using SearchAnnotation."""

from pathlib import Path
from typing import Annotated

from pydantic import Field

from otar_mcp.client import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


def _get_search_annotation_query() -> str:
    """Load the SearchAnnotation.gql file."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    query_file = project_root / "extracted_queries" / "search" / "SearchAnnotation.gql"

    if not query_file.exists():
        msg = f"SearchAnnotation.gql not found at {query_file}"
        raise FileNotFoundError(msg)

    with open(query_file, encoding="utf-8") as f:
        return f.read()


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
    try:
        # Load the query once
        query = _get_search_annotation_query()
    except FileNotFoundError as e:
        return {"error": str(e)}

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
                query,
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
