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
