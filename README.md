# Ratchet

**[getratchet.dev](https://getratchet.dev) · AI agents that only get better.**

Ratchet is a lightweight framework for building AI agents that continuously improve themselves — autonomously, over time, with minimal human involvement.

Most agent frameworks focus on what an agent *can do*. Ratchet focuses on how an agent *gets better*.

---

## The idea

Every time something breaks, falls short, or reveals a gap — the agent doesn't just fix it and move on. It asks:

- *Why* did this happen? (root cause)
- *What else* might have the same problem? (blast radius)
- *What prevents it from happening again?* (prevention)

Then it does the prevention work. Without being asked.

Over time, the loop compounds. Incidents decrease. Autonomy increases. Each click of the ratchet locks in — nothing regresses.

---

## How it works

Ratchet is mostly **conventions, not code**. A file structure, a set of processes, and prompt patterns that wire into your existing AI setup.

```
your-agent/
├── MEMORY.md          # Long-term memory — curated, evolving
├── BACKLOG.md         # Self-directed work queue — P1/P2/P3
├── context.json       # Authoritative state (location, units, preferences)
├── incidents/
│   ├── README.md      # Postmortem format spec
│   └── INC-001-*.md   # Incident logs
├── memory/
│   └── YYYY-MM-DD.md  # Daily logs
└── bin/               # Utility scripts
```

The agent reads these files, maintains them, and acts on them — continuously, across sessions.

---

## Core components

**Memory** — The agent wakes up fresh each session. These files are its continuity. MEMORY.md is curated long-term knowledge. Daily logs are raw notes. The agent synthesizes both.

**Incident loop** — Every failure gets a postmortem. Root cause, blast radius, prevention tasks. Prevention tasks go into the backlog. The backlog gets worked autonomously.

**Backlog** — A self-directed work queue. P1s execute immediately. P2s execute this week. P3s execute when there's bandwidth. The agent works through it without prompting.

**Context** — A single authoritative JSON file for state that should never be assumed: location, timezone, units, preferences. Always checked before creating anything time-sensitive.

**Review cadence** — Weekly synthesis. The agent reads the week's incidents, backlog, and memory; identifies patterns; updates MEMORY.md; reports to the human. Keeps the loop honest.

**Autonomy tiers** — Trust expands over time. Early on, the agent queues uncertain decisions. Over time, it makes more calls independently. Explicit, configurable, earned.

---

## Getting started

1. Fork this repo
2. Copy `template/` into your agent's working directory
3. Fill in `context.json` with your location, timezone, and preferences
4. Wire the heartbeat and weekly review prompts to your agent (see `docs/adapters/`)
5. Name your agent. Ours is [Pawl](examples/personal-assistant/).

---

## Adapters

Ratchet is platform-agnostic. The framework runs on whatever AI tooling you use.

- [OpenClaw](docs/adapters/openclaw.md) ← reference implementation

*More adapters welcome. See [contributing](#contributing).*

---

## Reference implementation

[Pawl](examples/personal-assistant/) is the agent we run on this framework, sanitized for public use. Every incident log, backlog entry, and memory file shown there is based on real usage.

INC-001 is a good place to start — a real bug, a real postmortem, and a worked example of the full prevention loop.

---

## Philosophy

An agent that improves itself is not magic. It's a feedback loop with memory and a bias toward action.

The ratchet metaphor is load-bearing: the pawl is the piece that locks each improvement in and prevents regression. Every incident closed, every prevention task done, every pattern identified — that's a click. Nothing goes backward.

The goal is an agent that, given enough time and enough loops, requires less and less from you — not because it's doing less, but because it's doing more right.

---

## Contributing

Ratchet is early. Contributions welcome:

- Adapters for other AI platforms (Claude Code, Cursor, etc.)
- Improved prompt patterns
- Additional template components
- Real-world incident examples (sanitized)

---

## License

MIT
