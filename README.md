# Ratchet

**[getratchet.dev](https://getratchet.dev) · The accountability layer for AI agents.**

Most AI frameworks ask: *can the agent do the task?*
Ratchet asks: *will it still work on Tuesday?*

Ratchet gives your agent structured memory, an incident loop, and evidence-based trust tiers — so mistakes get caught, fixes stick, and autonomy is earned, not assumed.

---

## Packages

Ratchet is a modular framework. Install what you need:

| Package | Description | Status |
|---------|-------------|--------|
| **[ratchet-core](packages/ratchet-core/)** | Agent lifecycle, module system, event bus, config | ✅ Ready |
| **[ratchet-memory](packages/ratchet-memory/)** | Fact extraction, retrieval, lifecycle, embeddings | ✅ Ready |
| **ratchet-pilot** | Self-improvement engine: backlog, incidents, trust tiers | ✅ Ready |
| **ratchet-factory** | Code generation, testing, deployment | ✅ Ready |
| **ratchet-research** | Deep research with vector DB storage | 🔜 Planned |
| **ratchet-ops** | Business process automation | 🔜 Planned |

### Quick start

```bash
pip install ratchet-core ratchet-memory
```

```python
from ratchet.core import Agent
from ratchet.memory import MemoryModule

agent = Agent(name="my-agent", config_path="config/context.json")
agent.register(MemoryModule())
await agent.start()
```

### Reference agent

[Pawl](agents/pawl/) is the reference implementation — a personal AI agent running on Ratchet. Every module, incident log, and capability shown in this repo is based on real usage.

---

## How it works

Every time something breaks, falls short, or reveals a gap — the agent doesn't just fix it and move on. It asks:

- *Why* did this happen? (root cause)
- *What else* might have the same problem? (blast radius)
- *What prevents it from happening again?* (prevention)

Then it does the prevention work. Without being asked.

Over time, the loop compounds. Incidents decrease. Autonomy increases. Each click of the ratchet locks in — nothing regresses.

---

## Architecture

```
packages/
├── ratchet-core/          # Agent, modules, event bus, config
├── ratchet-memory/        # Extract, retrieve, manage, embed
├── ratchet-pilot/         # Backlog, incidents, trust, guardrails
├── ratchet-factory/       # Code generation + deployment
├── ratchet-research/      # Deep research + vector DB
└── ratchet-ops/           # Business process automation

agents/
└── pawl/                  # Reference agent

website/                   # getratchet.dev (GitHub Pages)
docs/                      # Framework documentation
```

## Core concepts

**Memory** — The agent wakes up fresh each session. Ratchet Memory extracts facts, scores them by importance and recency, and injects the most relevant ones at session start. Nothing is lost.

**Incident loop** — Every failure gets a postmortem with root cause, blast radius, and prevention tasks. Prevention tasks go into the backlog and get worked autonomously.

**Trust tiers** — Autonomy expands as competence is demonstrated. T1 (read/respond) → T2 (schedule/organize) → T3 (external comms) → T4 (spend) → T5 (infrastructure). Evidence-based, not time-based.

**Modules** — Every capability is a module that implements `RatchetModule`. Modules communicate via the event bus, never by importing each other's internals. Add what you need, ignore what you don't.

---

## Contributing

Ratchet is early. Contributions welcome:

- New modules and adapters
- Improved prompt patterns
- Real-world incident examples (sanitized)
- Documentation and tutorials

---

## License

MIT
