from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryResultStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class QueryResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: QueryResultStatus = Field(
        ...,
        description="The status of the query result.",
    )
    data: Any | None = Field(
        None,
        description=(
            "The data returned by the query. Data could still be available even if the status is not success "
            "and it MUST be treated with caution as it may be INCOMPLETE or UNRELIABLE."
        ),
    )
    message: str | None = Field(
        None,
        description=(
            "The message associated with the query result. This field is typically used to provide additional "
            "information about the non-successful query result, such as error details or warnings."
        ),
    )

    @classmethod
    def create_success(cls, data: Any, **kwargs: Any) -> "QueryResult":
        return QueryResult(status=QueryResultStatus.SUCCESS, data=data, **kwargs)

    @classmethod
    def create_error(cls, message: str, **kwargs: Any) -> "QueryResult":
        return QueryResult(status=QueryResultStatus.ERROR, data=None, message=message, **kwargs)

    @classmethod
    def create_warning(cls, data: Any, message: str, **kwargs: Any) -> "QueryResult":
        return QueryResult(status=QueryResultStatus.WARNING, data=data, message=message, **kwargs)


class BatchQuerySingleResult(BaseModel):
    index: int = Field(
        ...,
        description="Index of the input variable set associated with the query result.",
    )
    id: str | None = Field(
        None,
        description=(
            "The value of the variable designated by the client inside the variable set, to be used as the "
            "identifier for this result."
        ),
    )
    result: QueryResult = Field(
        ...,
        description="The result of the individual query in the batch.",
    )


class BatchQueryStatusCounts(BaseModel):
    total: int
    successful: int
    failed: int
    warning: int


class BatchQueryResult(BaseModel):
    results: list[BatchQuerySingleResult]
    status_counts: BatchQueryStatusCounts
