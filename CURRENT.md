# CURRENT.md — What Pawl Is Building Right Now

This file is committed to GitHub at the end of every session and updated by heartbeats.
It is the single source of truth for in-flight work. If context compacts, start here.

## Active session
**Date:** 2026-02-28
**Status:** Late afternoon — major session complete, one open decision

## What shipped today

### Morning briefing upgrades
- [x] Calendar: today + tomorrow, travel keyword scanning
- [x] North Star section: 3 mission-aligned actions daily
- [x] Restart count bug fixed (INC-004)

### Calendar integration
- [x] Write scope authorized, 3 recurring events created
- [x] bin/travel-detect: scans 7 days for travel keywords
- [x] gcal-today: graceful degradation on auth failure
- [x] INC-006: OAuth client disabled — deferred fix

### Vehicle maintenance system
- [x] vehicles.md: full specs, part numbers, inventory, service history
- [x] cadence.json: 17 items across WRX/Tacoma/Outback
- [x] bin/cadence-check: pre-service checklists, "reply when done" prompt
- [x] bin/cadence-update: one-command service logging
- [x] bin/travel-detect: calendar travel scan
- [x] Outback P0141 logged, monitoring
- [x] Outback rear pads staged, rotors needed

### Growth / Ratchet
- [x] README overhaul (Issue #14 closed)
- [x] MIT license added
- [x] PRs opened: kaushikb11 #77, kyrolabs #155 (Issue #15 closed)
- [x] Cadence feature card on getratchet.dev
- [x] publish-process.md documented
- [x] unlock-capability prints publish checklist

### Process
- [x] AGENTS.md: parallel execution, routing discipline, vehicle logging, GitHub commit, publish process rules
- [x] INC-004, INC-005, INC-006 logged

## Open decision (needs Aaron)
**Process enforcement structure**: Aaron asked "gate during build, or end-of-session?"
- Option 2 (tool enforcement) partially live: unlock-capability prints checklist
- Full structural fix pending Aaron's answer
- Resume: ask Aaron to answer this when next session starts

## Blocked
- Google OAuth (INC-006): Cloud Console fix, Aaron's action when ready
- WRX filter reorder: order 15208AA170 qty 3 before June 2026
- Outback rear rotors: order before scheduling brake job
- Tacoma service day: waiting on weather + calendar

## Ratchet Memory Phase 1 — SHIPPED ✅
- [x] bin/memory-extract: extracts facts from session transcripts via LLM (isolated call)
- [x] bin/memory-retrieve: retrieves top relevant facts for session start
- [x] session-start: wired — shows top facts at session start
- [x] pre-compaction: wired — reminds to run memory-extract after session ends
- [x] Tested on 2026-02-28.md: 25 facts extracted, retrieval working
- [x] facts-2026-Q1.jsonl: 25 facts seeded
- Schema: id, content, category, tags, importance, tier, created, source_session, last_referenced, reference_count, supersedes, superseded_by, promoted, source_trust
- LLM calls use direct Anthropic API (urllib, no external deps)
- Next: Phase 2 (decay/promote/manage — Issue #17 → close and open #18)

## Next steps (in order)
1. Answer process enforcement question (Aaron)
2. Order WRX filters 15208AA170
3. Order Outback rear rotors
4. Fix Google OAuth when ready (Cloud Console)
5. Run memory-extract regularly after sessions to build fact base
5. Populate demo fixtures for Cadence in Mission Control
6. Screenshot getratchet.dev cadence card when browser available

## Resume instructions (after compaction)
1. Read SOUL.md, USER.md, MEMORY.md
2. Read this file
3. Read memory/2026-02-28.md for full session detail
4. First: ask Aaron about process enforcement structure (open decision above)
5. Vehicle service logging: run cadence-update silently when Aaron reports service done
6. Cadence IDs: `cadence-update --list` to see all
