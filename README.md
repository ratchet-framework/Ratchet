# Ratchet

**[getratchet.dev](https://getratchet.dev) · The accountability layer for AI agents.**

Most AI frameworks ask: *can the agent do the task?*
Ratchet asks: *will it still work on Tuesday?*

Ratchet gives your agent structured memory, an incident loop, and evidence-based trust tiers — so mistakes get caught, fixes stick, and autonomy is earned, not assumed.

---

## Quick start
```bash
pip install ratchet-core ratchet-memory ratchet-pilot ratchet-factory
ratchet init my-agent
cd my-agent
python my-agent.py
```

That's it. One command scaffolds a complete agent with memory, trust tiers, guardrails, a backlog, and an incident directory. The agent boots immediately.

---

## Packages

Ratchet is modular. Install what you need:

| Package | Description | Status |
|---------|-------------|--------|
| **[ratchet-core](packages/ratchet-core/)** | Agent lifecycle, module system, event bus, config | ✅ Ready |
| **[ratchet-memory](packages/ratchet-memory/)** | Fact extraction, retrieval, lifecycle, embeddings | ✅ Ready |
| **[ratchet-pilot](packages/ratchet-pilot/)** | Self-improvement engine: backlog, incidents, trust tiers | ✅ Ready |
| **[ratchet-factory](packages/ratchet-factory/)** | CLI scaffolding for agents and modules | ✅ Ready |
| **ratchet-research** | Deep research with vector DB storage | ✅ Ready |
| **ratchet-ops** | Business process automation | ✅ Ready |

### Create a new module
```bash
ratchet new module disk-monitor --description "Monitor disk usage and alert on thresholds"
```

Generates a complete package skeleton with `pyproject.toml`, `RatchetModule` implementation, and README — ready to `pip install -e` and register in your agent.

### Wire it up yourself
```python
from ratchet.core import Agent
from ratchet.memory import MemoryModule
from ratchet.pilot import PilotModule

agent = Agent(name="my-agent", config_path="config/context.json")
agent.register(MemoryModule())
agent.register(PilotModule())
await agent.start()
```

### Reference agent

[Pawl](agents/pawl/) is the reference implementation — a personal AI agent running on Ratchet in production. Every module, incident log, and capability shown in this repo is based on real usage.

---

## How it works

Every time something breaks, falls short, or reveals a gap — the agent doesn't just fix it and move on. It asks:

- *Why* did this happen? (root cause)
- *What else* might have the same problem? (blast radius)
- *What prevents it from happening again?* (prevention)

Then it does the prevention work. Without being asked.

Over time, the loop compounds. Incidents decrease. Autonomy increases. Each click of the ratchet locks in — nothing regresses.

---

## Core concepts

**Memory** — The agent wakes up fresh each session. Ratchet Memory extracts facts from transcripts, scores them by importance and recency, and injects the most relevant ones at session start. Nothing is lost.

**Incident loop** — Every failure gets a postmortem with root cause, blast radius, and prevention tasks. Prevention tasks go into the backlog and get worked autonomously.

**Trust tiers** — Autonomy expands as competence is demonstrated. T1 (read/respond) → T2 (schedule/organize) → T3 (external comms) → T4 (spend) → T5 (infrastructure). Evidence-based, not time-based. P1 incidents trigger automatic regression.

**Guardrails** — Preflight checks match actions against keyword rules before execution. Hard matches pause for human approval. Soft matches warn and proceed.

**Modules** — Every capability is a module that implements `RatchetModule`. Modules communicate via the event bus, never by importing each other's internals. Add what you need, ignore what you don't.

---

## Architecture
packages/
├── ratchet-core/          # Agent, modules, event bus, config
├── ratchet-memory/        # Extract, retrieve, manage, embed
├── ratchet-pilot/         # Backlog, incidents, trust, guardrails
├── ratchet-factory/       # CLI scaffolding for agents and modules
├── ratchet-research/      # Deep research + vector DB (planned)
└── ratchet-ops/           # Business process automation (planned)
agents/
└── pawl/                  # Reference agent (production)
website/                   # getratchet.dev (GitHub Pages)
docs/                      # Framework documentation

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