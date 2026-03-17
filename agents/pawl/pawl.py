"""Pawl — Ratchet reference agent."""

import asyncio
import logging
from ratchet.core import Agent
from ratchet.memory import MemoryModule
from ratchet.pilot import PilotModule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    agent = Agent(name="Pawl", config_path="agents/pawl/config/context.json")
    agent.register(MemoryModule())
    agent.register(PilotModule())

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
