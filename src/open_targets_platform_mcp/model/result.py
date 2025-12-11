from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class QueryResultStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class QueryResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: QueryResultStatus
    result: Any | None = None
    message: Any | None = None

    @classmethod
    def create_success(cls, data: Any, **kwargs: Any) -> "QueryResult":
        return QueryResult(status=QueryResultStatus.SUCCESS, result=data, **kwargs)

    @classmethod
    def create_error(cls, message: Any, **kwargs: Any) -> "QueryResult":
        return QueryResult(status=QueryResultStatus.ERROR, result=None, message=message, **kwargs)

    @classmethod
    def create_warning(cls, data: Any, message: Any, **kwargs: Any) -> "QueryResult":
        return QueryResult(status=QueryResultStatus.WARNING, result=data, message=message, **kwargs)


class BatchQuerySingleResult(BaseModel):
    index: int
    key: str | None
    result: QueryResult


class BatchQuerySummary(BaseModel):
    total: int
    successful: int
    failed: int
    warning: int


class BatchQueryResult(BaseModel):
    results: list[BatchQuerySingleResult]
    summary: BatchQuerySummary
