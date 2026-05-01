from pydantic import BaseModel, Field

from open_targets_platform_mcp.model.query_result import BatchQueryResult


class SearchEntitiesResult(BaseModel):
    batch_query_result: BatchQueryResult = Field(
        ...,
        description="The status of the query result.",
    )
