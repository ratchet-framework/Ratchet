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
