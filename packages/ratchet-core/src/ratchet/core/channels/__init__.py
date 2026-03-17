"""Abstract base for communication channels."""

from abc import ABC, abstractmethod
from typing import Any


class Channel(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def send(self, message: str, **kwargs: Any) -> None: ...

    @abstractmethod
    async def listen(self) -> None: ...

    async def send_alert(self, message: str, severity: str = "info", **kwargs: Any) -> None:
        prefix = {"info": "ℹ️", "warning": "⚠️", "error": "🚨"}.get(severity, "")
        await self.send(f"{prefix} {message}", **kwargs)

    async def shutdown(self) -> None:
        pass
