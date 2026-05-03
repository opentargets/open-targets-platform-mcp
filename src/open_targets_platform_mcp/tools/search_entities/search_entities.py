"""Tool for executing entity search queries."""

from typing import Annotated

from pydantic import Field

from open_targets_platform_mcp.model.query_result import QueryResultStatus
from open_targets_platform_mcp.model.search_entities_result import SearchEntitiesResultHit
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
            description="List of search queries",
            examples=[
                ["BRCA1"],
                ["breast cancer", "aspirin"],
            ],
        ),
    ],
) -> Annotated[
    dict[str, list[SearchEntitiesResultHit]],
    Field(description="Search entities result"),
]:
    batch_query_result = await batch_query_with_jq(
        SEARCH_ENTITY_QUERY,
        [{VARIABLE_FIELD: query_string} for query_string in query_strings],
        VARIABLE_FIELD,
    )

    result = dict[str, list[SearchEntitiesResultHit]]()
    for query_result in batch_query_result.results:
        if query_result.id is None:
            continue
        query_string = query_result.id
        entities = list[SearchEntitiesResultHit]()
        if query_result.result.status == QueryResultStatus.SUCCESS and query_result.result.data is not None:
            for hit in query_result.result.data.get("search", {}).get("hits", []):
                entities.append(SearchEntitiesResultHit(entity_id=hit["id"], entity_type=hit["entity"]))
        result[query_string] = entities

    return result
