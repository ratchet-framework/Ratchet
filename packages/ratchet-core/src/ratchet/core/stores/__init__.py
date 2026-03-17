"""Abstract base for state storage backends."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class Store(ABC):
    @abstractmethod
    async def read(self, key: str) -> Optional[Any]: ...

    @abstractmethod
    async def write(self, key: str, value: Any) -> None: ...

    @abstractmethod
    async def append(self, key: str, value: Any) -> None: ...

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]: ...

    @abstractmethod
    async def delete(self, key: str) -> bool: ...
