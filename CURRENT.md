# CURRENT.md — What Pawl Is Building Right Now

This file is committed to GitHub at the end of every session and updated by heartbeats.
It is the single source of truth for in-flight work. If context compacts, start here.

## Active session
**Date:** 2026-02-28 (continuing after Aaron's D&D break)
**Status:** Autonomous work completed, ready for Aaron's return

## What shipped today (complete)

### Memory + Compaction Test
- [x] Ratchet Memory Phase 1 — extraction + LLM retrieval (51 facts)
- [x] Ratchet Memory Phase 2 — lifecycle scoring, contradiction detection
- [x] Ratchet Memory Phase 3 — semantic embeddings + cosine similarity
- [x] Compaction test — proved context survives session boundary
- [x] All three phases published to getratchet.dev (21/34 capabilities)
- [x] GitHub Issues #16-19 created, #17-19 closed

### Infrastructure + Orchestration
- [x] Orchestration architecture doc — Discord + worker droplet strategy
- [x] GitHub Issues #20-22 created (routing, worker, primitive)
- [x] Discord setup guide — complete step-by-step for Aaron

### Incident Resolution
- [x] INC-007 remediated — PROCESS.md parallel execution rule + metrics recurrence detection

### Vehicle Data
- [x] Outback rear rotor p/n confirmed: **26700AL03A**
- [x] Pricing research — WRX filter + rotors with links
- [x] order-links.md created for quick reference

### Autonomous Work (while Aaron played D&D)
- [x] MEMORY.md updated with session learnings
- [x] Daily log expanded with all deliverables
- [x] Ratchet scripts published to `reference-implementations/bin/`
- [x] Pre-compaction state snapshot

## Open — needs Aaron
- Discord setup: server creation + bot token (Aaron's action)
- WRX filter order: 15208AA170 qty 3 (when Aaron ready)
- Outback rotor order: 26700AL03A qty 2 (when Aaron ready)
- Google OAuth re-auth (when ready, not urgent)

## Blocked
- Discord integration pending server setup
- Google Calendar write scope (OAuth client disabled, INC-006)

## Next steps (in order)
1. **Discord setup** — Aaron creates server, provides bot token, Pawl configures OpenClaw
2. **Part orders** — use order-links.md for quick reference
3. **Phase 4: Semantic retrieval** — index workspace for cross-incident pattern detection
4. **Worker droplet** — when sub-agent load justifies it (1-2 months out)

## Resume instructions (after any compaction)
1. Run `python3 workspace/bin/session-start` — reads this file, surfaces open decisions, loads memory facts
2. First message to Aaron: "I'm back. Here's what I have from the last session."
3. Next: Ask Aaron about Discord setup progress
4. Then: Continue with part orders + Phase 4 planning

## Summary of today's work

**Morning:** Compaction test proved memory system works end-to-end.

**Afternoon:** Shipped Ratchet Memory phases 1-3, designed orchestration architecture, fixed INC-007, confirmed Outback rotor p/n.

**Evening (autonomous):** Updated MEMORY.md, created order links, wrote Discord guide, published scripts to GitHub, prepared everything for Aaron's return.

**Metrics:**
- 21/34 capabilities unlocked (was 20)
- Issues #16-22 created, #17-19 closed
- Memory facts: 51 extracted and stored
- Documentation: 5 new/updated concept docs + Discord setup guide
- GitHub commits today: 10+

**State at Aaron's return:** All core infrastructure in place. Ready to deploy Discord and move to Phase 4 (semantic retrieval). No blockers — everything is either done or waiting on Aaron's decision/action.
