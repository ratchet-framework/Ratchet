"""Base class all Ratchet modules implement."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class RatchetModule(ABC):
    """
    Base class for all Ratchet modules.

    Every module (memory, pilot, factory, research, ops, etc.) implements
    this interface. The Agent registers modules at startup and calls their
    lifecycle hooks during operation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Module identifier (e.g., 'memory', 'pilot', 'research')."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version string."""
        ...

    @property
    def dependencies(self) -> list[str]:
        """List of required module names. Default: none."""
        return []

    @abstractmethod
    async def initialize(self, agent: "Agent", config: dict[str, Any]) -> None:
        """Called once when the agent starts."""
        ...

    @abstractmethod
    async def on_heartbeat(self) -> Optional[dict[str, Any]]:
        """Called on each heartbeat cycle. Return status dict or None."""
        ...

    async def on_session_start(self, context: dict[str, Any]) -> None:
        """Called when a new session begins."""
        pass

    async def on_session_end(self, context: dict[str, Any]) -> None:
        """Called when a session ends (before compaction)."""
        pass

    async def on_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Called when bus publishes an event this module subscribes to."""
        pass

    async def shutdown(self) -> None:
        """Cleanup on agent shutdown."""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} v{self.version}>"
