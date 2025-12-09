"""Tool for executing entity search queries."""

from typing import Annotated

from pydantic import Field

from open_targets_platform_mcp.model.result import BatchQueryResult, QueryResult
from open_targets_platform_mcp.tools.batch_query.batch_query import batch_query_with_jq

VARIABLE_FIELD = "queryString"
JQ_FILTER = ".data.search.hits[:3] | map({id, entity})"
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


async def search_entities(
    query_strings: Annotated[
        list[str],
        Field(
            description="List of search query strings to find entities (e.g., ['BRCA1', 'breast cancer', 'aspirin'])",
        ),
    ],
) -> BatchQueryResult | QueryResult:
    """Search for entities' IDs and types."""
    batch_query_result = await batch_query_with_jq(
        SEARCH_ENTITY_QUERY,
        [{VARIABLE_FIELD: query_string} for query_string in query_strings],
        VARIABLE_FIELD,
        JQ_FILTER,
    )

    if isinstance(batch_query_result, QueryResult):
        return batch_query_result

    return batch_query_result
