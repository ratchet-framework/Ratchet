#!/bin/bash
# Run this from your Ratchet repo root (C:/Projects/Ratchet on the modularize branch)
# It creates all the Python module files for the scaffold.

set -e

echo "🔩 Creating ratchet-core package files..."

# --- ratchet-core ---

cat > packages/ratchet-core/pyproject.toml << 'PYEOF'
[project]
name = "ratchet-core"
version = "0.1.0"
description = "The accountability layer for AI agents — core framework"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Aaron Benson" },
]
keywords = ["ai", "agents", "ratchet", "self-improvement", "autonomy"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
dependencies = []

[project.urls]
Homepage = "https://getratchet.dev"
Repository = "https://github.com/ratchet-framework/Ratchet"
Issues = "https://github.com/ratchet-framework/Ratchet/issues"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ratchet"]

[tool.hatch.build.targets.editable]
packages = ["src/ratchet"]
PYEOF

cat > packages/ratchet-core/README.md << 'MDEOF'
# ratchet-core

The kernel of the [Ratchet framework](https://getratchet.dev) — the accountability layer for AI agents.

`ratchet-core` provides:

- **Agent** — the runtime that manages module lifecycle, heartbeat loops, and sessions
- **RatchetModule** — the base class every module implements
- **EventBus** — async pub/sub for inter-module communication without tight coupling
- **Config** — context.json loading and validation
- **Channels** — abstract interface for communication (Telegram, Discord, CLI)
- **Stores** — abstract interface for state persistence (flat files, SQLite)

## Install

```bash
pip install ratchet-core
```

## Quick start

```python
from ratchet.core import Agent

agent = Agent(name="my-agent", config_path="config/context.json")
await agent.start()
```

## License

MIT
MDEOF

cat > packages/ratchet-core/src/ratchet/core/__init__.py << 'PYEOF'
"""ratchet.core — The kernel that everything else plugs into."""

from ratchet.core.module import RatchetModule
from ratchet.core.agent import Agent
from ratchet.core.bus import EventBus
from ratchet.core.config import load_config

__all__ = ["RatchetModule", "Agent", "EventBus", "load_config"]
PYEOF

cat > packages/ratchet-core/src/ratchet/core/module.py << 'PYEOF'
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
PYEOF

cat > packages/ratchet-core/src/ratchet/core/bus.py << 'PYEOF'
"""Simple async pub/sub event bus for inter-module communication."""

import asyncio
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger("ratchet.core.bus")

EventHandler = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """
    Lightweight pub/sub bus. Modules communicate through events
    without importing each other.

    Event naming convention: "module_name.event_name"
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    async def publish(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        if payload is None:
            payload = {}
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return
        results = await asyncio.gather(
            *[h(event_type, payload) for h in handlers],
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Handler {handlers[i]} failed on {event_type}: {result}")

    @property
    def event_types(self) -> list[str]:
        return list(self._subscribers.keys())
PYEOF

cat > packages/ratchet-core/src/ratchet/core/config.py << 'PYEOF'
"""Configuration loading and validation for Ratchet agents."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("ratchet.core.config")

REQUIRED_FIELDS = {"name", "timezone"}

DEFAULTS = {
    "units": "imperial",
    "locale": "en-US",
    "heartbeat_interval_minutes": 30,
    "quiet_hours": {"start": "23:00", "end": "07:00"},
}


def load_config(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    missing = REQUIRED_FIELDS - set(config.keys())
    if missing:
        raise ValueError(f"Missing required config fields: {missing}")

    for key, default in DEFAULTS.items():
        if key not in config:
            config[key] = default

    logger.info(f"Loaded config for agent '{config['name']}' (tz: {config['timezone']})")
    return config
PYEOF

cat > packages/ratchet-core/src/ratchet/core/agent.py << 'PYEOF'
"""Agent — the runtime that ties modules, bus, and config together."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from ratchet.core.bus import EventBus
from ratchet.core.config import load_config
from ratchet.core.module import RatchetModule

logger = logging.getLogger("ratchet.core.agent")


class Agent:
    """The Ratchet agent runtime."""

    def __init__(self, name: str, config_path: str | Path, workspace: str | Path | None = None) -> None:
        self.name = name
        self.config = load_config(config_path)
        self.workspace = Path(workspace) if workspace else Path(config_path).parent.parent
        self.bus = EventBus()
        self._modules: dict[str, RatchetModule] = {}
        self._running = False

    def register(self, module: RatchetModule) -> "Agent":
        for dep in module.dependencies:
            if dep not in self._modules:
                raise RuntimeError(f"Module '{module.name}' requires '{dep}' — register it first.")
        if module.name in self._modules:
            raise RuntimeError(f"Module '{module.name}' is already registered.")
        self._modules[module.name] = module
        logger.info(f"Registered module: {module}")
        return self

    def get_module(self, name: str) -> Optional[RatchetModule]:
        return self._modules.get(name)

    @property
    def modules(self) -> list[RatchetModule]:
        return list(self._modules.values())

    async def start(self) -> None:
        logger.info(f"Starting agent '{self.name}' with {len(self._modules)} module(s)")
        for module in self._modules.values():
            module_config = self.config.get(module.name, {})
            await module.initialize(self, module_config)
            logger.info(f"Initialized: {module}")
        self._running = True
        await self.bus.publish("agent.started", {"agent": self.name})

    async def stop(self) -> None:
        self._running = False
        for module in reversed(list(self._modules.values())):
            try:
                await module.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {module}: {e}")
        await self.bus.publish("agent.stopped", {"agent": self.name})

    async def session_start(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        ctx["agent"] = self.name
        for module in self._modules.values():
            await module.on_session_start(ctx)
        await self.bus.publish("agent.session_start", ctx)
        return ctx

    async def session_end(self, context: dict[str, Any] | None = None) -> None:
        ctx = context or {}
        for module in self._modules.values():
            await module.on_session_end(ctx)
        await self.bus.publish("agent.session_end", ctx)

    async def heartbeat(self) -> dict[str, Any]:
        report: dict[str, Any] = {}
        for module in self._modules.values():
            try:
                status = await module.on_heartbeat()
                if status:
                    report[module.name] = status
            except Exception as e:
                logger.error(f"Heartbeat failed for {module.name}: {e}")
                report[module.name] = {"error": str(e)}
                await self.bus.publish("pilot.incident_detected", {
                    "source": module.name, "error": str(e), "type": "heartbeat_failure"
                })
        await self.bus.publish("agent.heartbeat", report)
        return report

    async def run(self, heartbeat_interval: int | None = None) -> None:
        await self.start()
        if heartbeat_interval is None:
            heartbeat_interval = self.config.get("heartbeat_interval_minutes", 30) * 60
        try:
            while self._running:
                await self.heartbeat()
                await asyncio.sleep(heartbeat_interval)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()
PYEOF

cat > packages/ratchet-core/src/ratchet/core/channels/__init__.py << 'PYEOF'
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
PYEOF

cat > packages/ratchet-core/src/ratchet/core/stores/__init__.py << 'PYEOF'
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
PYEOF

echo ""
echo "🔩 Creating ratchet-memory package files..."

# --- ratchet-memory ---

cat > packages/ratchet-memory/pyproject.toml << 'PYEOF'
[project]
name = "ratchet-memory"
version = "0.1.0"
description = "Persistent agent memory for the Ratchet framework"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Aaron Benson" },
]
dependencies = [
    "ratchet-core>=0.1.0",
]

[project.urls]
Homepage = "https://getratchet.dev"
Repository = "https://github.com/ratchet-framework/Ratchet"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ratchet"]

[tool.hatch.build.targets.editable]
packages = ["src/ratchet"]
PYEOF

cat > packages/ratchet-memory/README.md << 'MDEOF'
# ratchet-memory

Persistent agent memory for the [Ratchet framework](https://getratchet.dev).

## Install

```bash
pip install ratchet-memory
```

## License

MIT
MDEOF

cat > packages/ratchet-memory/src/ratchet/memory/__init__.py << 'PYEOF'
"""ratchet.memory — Persistent agent memory with fact extraction and retrieval."""

from ratchet.memory.module import MemoryModule

__all__ = ["MemoryModule"]
PYEOF

cat > packages/ratchet-memory/src/ratchet/memory/module.py << 'PYEOF'
"""MemoryModule — Ratchet's persistent memory system.

Modular version of the reference implementation scripts:
    bin/memory-extract  -> ratchet.memory.extract
    bin/memory-retrieve -> ratchet.memory.retrieve
    bin/memory-manage   -> ratchet.memory.manage
    bin/memory-embed    -> ratchet.memory.embed
"""

from typing import Any, Optional
from ratchet.core.module import RatchetModule


class MemoryModule(RatchetModule):
    """Persistent agent memory with fact extraction, retrieval, and lifecycle."""

    name = "memory"
    version = "0.1.0"

    def __init__(self) -> None:
        self.agent = None
        self.facts_dir = None
        self.provider = "anthropic"
        self.embedding_provider = "tfidf"
        self.max_retrieval = 15

    async def initialize(self, agent, config: dict[str, Any]) -> None:
        self.agent = agent
        self.facts_dir = config.get("facts_dir", "memory/facts")
        self.provider = config.get("provider", "anthropic")
        self.embedding_provider = config.get("embedding_provider", "tfidf")
        self.max_retrieval = config.get("max_retrieval", 15)
        agent.bus.subscribe("agent.session_end", self._on_session_end_event)

    async def on_session_start(self, context: dict[str, Any]) -> None:
        # TODO: Port from reference-implementations/bin/memory-retrieve
        pass

    async def on_session_end(self, context: dict[str, Any]) -> None:
        # TODO: Port from reference-implementations/bin/memory-extract
        pass

    async def on_heartbeat(self) -> Optional[dict[str, Any]]:
        return {"status": "healthy", "provider": self.provider, "facts_dir": self.facts_dir}

    async def _on_session_end_event(self, event_type: str, payload: dict[str, Any]) -> None:
        await self.on_session_end(payload)
        await self.agent.bus.publish("memory.facts_extracted", {"source": "session_end"})
PYEOF

echo ""
echo "🔩 Creating Pawl agent files..."

# --- Pawl agent ---

cat > agents/pawl/config/context.json << 'JSONEOF'
{
  "name": "Pawl",
  "timezone": "America/New_York",
  "units": "imperial",
  "locale": "en-US",
  "location": {
    "city": "Raleigh",
    "state": "NC",
    "country": "US"
  },
  "heartbeat_interval_minutes": 30,
  "quiet_hours": {
    "start": "23:00",
    "end": "07:00"
  },
  "memory": {
    "facts_dir": "memory/facts",
    "provider": "anthropic",
    "embedding_provider": "tfidf",
    "max_retrieval": 15
  }
}
JSONEOF

cat > agents/pawl/pawl.py << 'PYEOF'
"""Pawl — Ratchet reference agent."""

import asyncio
import logging
from ratchet.core import Agent
from ratchet.memory import MemoryModule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    agent = Agent(name="Pawl", config_path="agents/pawl/config/context.json")
    agent.register(MemoryModule())

    await agent.start()
    print(f"\n✅ Agent '{agent.name}' started with {len(agent.modules)} module(s):")
    for mod in agent.modules:
        print(f"   {mod}")

    report = await agent.heartbeat()
    print(f"\n💓 Heartbeat report:")
    for name, status in report.items():
        print(f"   {name}: {status}")

    await agent.stop()
    print(f"\n🔩 Agent stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
PYEOF

echo ""
echo "✅ All scaffold files created!"
echo ""
echo "Next: install Python 3.10+ if you haven't, then run:"
echo "  pip install -e packages/ratchet-core -e packages/ratchet-memory"
echo "  python agents/pawl/pawl.py"
