# CURRENT.md — What Pawl Is Building Right Now

This file is committed to GitHub at the end of every session and updated by heartbeats.
It is the single source of truth for in-flight work. If context compacts, start here.

## Active session
**Date:** 2026-02-28
**Status:** End of day — compaction test pending

## What shipped today (complete)

### Morning briefing
- [x] Calendar: today + tomorrow, travel keyword scanning
- [x] North Star section: 3 mission-aligned actions daily
- [x] Restart count bug fixed (INC-004)

### Calendar integration
- [x] Write scope authorized, 3 recurring events created (Monthly Milestone, Monthly Sync, Quarterly NS Review)
- [x] bin/travel-detect: scans 7 days for travel keywords
- [x] gcal-today: graceful degradation on auth failure
- [x] INC-006: OAuth client disabled — deferred, don't rush

### Vehicle maintenance system
- [x] vehicles.md: full specs, part numbers, inventory, service history (WRX/Tacoma/Outback)
- [x] cadence.json: 17 items with thresholds, pre-service checklists
- [x] bin/cadence-check + bin/cadence-update: one-command service logging
- [x] Outback P0141 (secondary O2 sensor) logged, monitoring at 88,191 mi
- [x] Outback rear brakes: pads staged 26696AN00A ✅, rotors still needed

### Session continuity system
- [x] PROCESS.md: single authoritative process file
- [x] bin/pre-compaction: verifies state, commits, reports gaps
- [x] bin/session-start: restores context, surfaces open decisions
- [x] bin/verify-publish: post-action publish verification, 5 gates, publish-log.json
- [x] AGENTS.md: all rules updated, no-quick-task-exception enforced

### Ratchet Memory Phase 1 — JUST SHIPPED
- [x] bin/memory-extract: LLM fact extraction from session transcripts
- [x] bin/memory-retrieve: scores + retrieves relevant facts for session start
- [x] memory/facts-2026-Q1.jsonl: 51 facts extracted from today's session
- [x] Wired into bin/session-start and bin/pre-compaction
- [x] GitHub Issues #16-19 created (Intelligence milestone)
- [x] Architecture doc: ratchet/docs/adaptive-memory.md (reviewed by Claude Opus)

### Growth / Ratchet
- [x] README overhaul (Issue #14 closed)
- [x] MIT license
- [x] PRs: kaushikb11/awesome-llm-agents #77, kyrolabs/awesome-agents #155 (Issue #15 closed)
- [x] Cadence + session-continuity feature cards on getratchet.dev
- [x] publish-process.md, verify-publish wired into pre-compaction + heartbeat

### Incidents
- [x] INC-004: briefing restart count (resolved)
- [x] INC-005: parallel execution promise (resolved)
- [x] INC-006: Google OAuth disabled (blocked on Aaron)
- [x] INC-007: parallel execution repeated, P2 (open prevention tasks)

## Open — needs Aaron
- INC-007 prevention tasks: 3 open items (add to PROCESS.md, recurrence detection in metrics)
- INC-006: fix Google OAuth (Cloud Console, Aaron's action — don't rush)
- Order WRX filters: 15208AA170, qty 3 (needed before June 2026)
- Order Outback rear rotors (pads staged, rotors needed)
- Tacoma service day: parts staged, waiting on weather + open calendar weekend

## Blocked
- Google Calendar: OAuth client disabled (INC-006)
- Tacoma service: waiting on weather

## Ratchet Memory Phase 2 — SHIPPED (2026-02-28)
- [x] bin/memory-manage: weekly lifecycle manager (decay, promote, purge, contradiction detection)
- [x] bin/memory-extract: tier detection (permanent/transient keywords), importance modifiers (+0.2 remember, +0.15 action-required)
- [x] bin/memory-retrieve: recency boost already present (e^(-0.023×days)), permanent/transient/superseded handling verified
- [x] Friday review cron updated to run memory-manage and include 🧠 Memory section in weekly report
- [x] Architecture: append-only JSONL; purge uses temp file swap; permanent tier never touched; contradictions flagged only

## Next steps (in order)
1. ~~Ratchet Memory Phase 3: semantic embeddings when >500 facts (Issue #19)~~ ✅ **Shipped**
2. INC-007 prevention tasks: update PROCESS.md, add recurrence detection to metrics
3. Discord integration research + roadmap (Issue TBD)
4. Second droplet architecture (Issue TBD)
5. Screenshot session-continuity + cadence cards for getratchet.dev

## Resume instructions (after compaction)
1. Run `python3 workspace/bin/session-start` — reads this file, surfaces open decisions, loads memory facts
2. First message to Aaron: "I'm back. Here's what I have from the last session." Then show session-start output.
3. Vehicle service logging rule: run cadence-update silently when Aaron reports a service done
4. INC-007 has 3 open prevention tasks — work autonomously: update PROCESS.md, add recurrence detection
5. Ratchet Memory Phase 1 is live: 51 facts in memory/facts-2026-Q1.jsonl
6. Phase 2 is next when Aaron says go

## The memory test
This is the first session where Ratchet Memory Phase 1 is active.
If session-start surfaces relevant facts from today without Aaron re-explaining them — the test passes.
Watch for: Tacoma brakes (overdue), WRX filter (0 in stock), INC-007, Outback O2 sensor monitoring.
