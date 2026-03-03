from dataclasses import dataclass
from typing import Generic, TypeVar, cast

T = TypeVar("T")


@dataclass(frozen=True)
class CacheKey(Generic[T]):
    name: str


class CacheStore:
    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def set(self, key: CacheKey[T], value: T) -> None:
        self._data[key.name] = value

    def get(self, key: CacheKey[T]) -> T:
        return cast("T", self._data[key.name])


cache = CacheStore()
