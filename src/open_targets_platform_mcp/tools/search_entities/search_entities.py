"""Tool for executing entity search queries."""

from typing import Annotated

from fastmcp.exceptions import ToolError
from pydantic import Field

from open_targets_platform_mcp.model.query_result import QueryResultStatus
from open_targets_platform_mcp.model.search_entities_result import SearchEntitiesFoundEntity
from open_targets_platform_mcp.tools.batch_query.batch_query import batch_query_with_jq

VARIABLE_FIELD = "queryString"
SEARCH_ENTITY_QUERY = """
query searchEntity($queryString: String!) {
  search(queryString: $queryString) {
    total
    hits {
      id
      entity
    }
  }
}
"""


async def search_entities(
    query_strings: Annotated[
        list[str],
        Field(
            description="List of search queries.",
            min_length=1,
            examples=[["BRCA1", "aspirin"]],
        ),
    ],
) -> Annotated[
    dict[str, list[SearchEntitiesFoundEntity]],
    "Top 3 hits for each query string, with entity ID and type.",
]:
    batch_query_result = await batch_query_with_jq(
        SEARCH_ENTITY_QUERY,
        [{VARIABLE_FIELD: query_string} for query_string in query_strings],
        VARIABLE_FIELD,
    )

    try:
        result = dict[str, list[SearchEntitiesFoundEntity]]()
        for query_result in batch_query_result.results:
            if query_result.id is None:
                continue
            query_string = query_result.id
            entities = list[SearchEntitiesFoundEntity]()
            if query_result.result.status == QueryResultStatus.SUCCESS and query_result.result.data is not None:
                for hit in query_result.result.data.get("search", {}).get("hits", [])[:3]:
                    entities.append(SearchEntitiesFoundEntity(id=hit["id"], type=hit["entity"]))
            result[query_string] = entities
    except Exception as e:
        msg = f"Failed to process batch query results: {e}"
        raise ToolError(msg) from e

    return result
