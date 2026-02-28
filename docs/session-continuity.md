# Session Continuity

Agents reset between sessions. Most frameworks treat this as a memory problem. Ratchet treats it as an engineering problem — with deterministic, verifiable solutions at every layer.

## The two distinct problems

Most agent memory work (MemGPT, Mem0) focuses on **fact retrieval**: storing information so it can be found later. That's necessary but not sufficient.

Ratchet addresses a second, harder problem: **behavioral consistency** — ensuring the agent follows the same processes and maintains the same operational state regardless of how many sessions have passed or how full the context window is.

These need different solutions.

## The Ratchet approach

### Layer 1 — Structured handoff (deterministic)

`CURRENT.md` is a living document committed to GitHub after every session. It contains:
- Exact in-flight state: what's built, what's blocked, what's open
- Open decisions awaiting the human
- Explicit resume instructions for the next session

No inference required. The next session reads this file and resumes exactly.

### Layer 2 — Verified persistence (automated)

`bin/pre-compaction` runs before context fills and verifies:
- Daily memory log exists and has content
- CURRENT.md contains today's date and resume instructions
- MEMORY.md was updated recently
- Git is clean — no uncommitted changes
- Ratchet repo is pushed to GitHub
- No open incident prevention tasks were skipped

Reports gaps. Auto-commits if safe. Won't let compaction happen with state un-captured.

### Layer 3 — Context restoration (systematic)

`bin/session-start` runs at the top of every new session and:
- Reads CURRENT.md and surfaces open decisions immediately
- Surfaces the next steps in priority order
- Checks open incidents and cadence alerts
- Verifies system health

Takes 3 seconds. Costs nothing. Removes the "where were we?" startup tax entirely.

### Layer 4 — Publish verification (accountability)

`bin/verify-publish <capability-slug>` checks after every new capability:
- Feature card updated on getratchet.dev?
- Concept doc exists in ratchet/docs/?
- Screenshots committed from demo environment?
- Ratchet repo pushed?

Logs results to `publish-log.json`. The pre-compaction script flags any capabilities built but not verified.

## What this solves that memory retrieval doesn't

Mem0 and Letta are excellent at answering "what did the user say about X?" They don't answer "did the agent follow the publish process for the cadence capability it built on Saturday?" 

Ratchet's session continuity layer is an operations layer, not a knowledge layer. It ensures:
- Process gates are followed consistently
- State is never lost between sessions
- The agent is accountable to its own defined processes
- Humans can verify what was done and when

## Data model

```
workspace/
├── ratchet/CURRENT.md    # In-flight state — committed after every session
├── MEMORY.md             # Curated long-term knowledge
├── memory/YYYY-MM-DD.md  # Daily raw logs
├── publish-log.json      # Verification audit trail
└── bin/
    ├── pre-compaction    # Run before context fills
    ├── session-start     # Run at session start
    └── verify-publish    # Run after publishing a capability
```

## What's next (Phase 3+)

- **Semantic retrieval**: index workspace content for vector search — find relevant context without reading every file
- **Automatic extraction**: important facts captured from conversations without manual logging
- **Behavioral audit**: weekly metrics on process compliance, not just operational health
