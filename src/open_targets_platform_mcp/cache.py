import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class AsyncCache(Generic[T]):
    def __init__(self, factory: Callable[[], Coroutine[Any, Any, T]] | None = None, *, is_eager: bool = False) -> None:
        self._factory = factory
        self._value: T | None = None
        self.is_eager = is_eager
        self._lock = asyncio.Lock()

    def set_factory(self, factory: Callable[[], Coroutine[Any, Any, T]]) -> None:
        self._factory = factory

    async def get(self) -> T:
        async with self._lock:
            if self._value is None:
                if self._factory is None:
                    msg = "Cache does not have a factory method"
                    raise RuntimeError(msg)
                self._value = await self._factory()
            return self._value

    def set(self, value: T) -> None:
        self._value = value
