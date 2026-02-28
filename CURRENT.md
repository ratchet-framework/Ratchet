# CURRENT.md — What Pawl Is Building Right Now

This file is committed to GitHub at the end of every session and updated by heartbeats.
It is the single source of truth for in-flight work. If context compacts, start here.

## Active session
**Date:** 2026-02-28
**Status:** Active — major session, many systems built

## What shipped today

### Morning briefing upgrades
- [x] Calendar section: today + tomorrow events, travel keyword scanning
- [x] North Star section: 3 mission-aligned actions daily (reads NORTH-STAR.md, CURRENT.md, trust.json)
- [x] Restart count bug fixed (INC-004): now time-bounded to last 24h

### Calendar integration
- [x] Google Calendar write scope authorized
- [x] 3 recurring events created: Monthly Milestone Check, Monthly Sync, Quarterly North Star Review
- [x] gcal-today: graceful degradation on auth failure (INC-006)
- [x] bin/travel-detect: scans next 7 days for travel keywords, Telegram alert, deduplication
- [x] Travel detection wired into heartbeat

### Vehicle maintenance system (new)
- [x] vehicles.md: full specs for WRX, Tacoma, Outback (oil type/capacity, filter #s, drain bolt, washers)
- [x] Inventory catalogued: 10x Outback filters, 1x Tacoma filter, 10x Tacoma crush washers, 0x WRX filters
- [x] cadence.json: 17 items with thresholds, alert windows, pre-service specs
- [x] bin/cadence-check: upgraded with pre-service checklists + "reply when done" prompt
- [x] bin/cadence-update: one-command service logging, resets alert state
- [x] Outback CEL: P0141 (secondary O2 sensor replaced 2026-02-28), monitoring at 88,191 mi
- [x] Outback rear brakes: pads staged (26696AN00A), rotors still needed

### Growth / Ratchet
- [x] README overhaul: screenshots, trust tiers, metrics, adapters table (Issue #14 closed)
- [x] MIT license added to Ratchet repo
- [x] Awesome-list PRs opened: kaushikb11/awesome-llm-agents #77, kyrolabs/awesome-agents #155
- [x] Issue #15 closed

### Process improvements
- [x] AGENTS.md: parallel execution rule, Telegram routing discipline, vehicle service logging, GitHub commit rule
- [x] INC-004 (briefing restart count), INC-005 (parallel execution promise), INC-006 (OAuth client disabled)

## Current status by vehicle
- WRX: oil ✅ (Jun 2026), tires 🔴 overdue, brakes ✅, filter 0 in stock ⚠️
- Tacoma: oil 🟡 (Mar 2026), brakes 🔴 overdue (44mo), diff service staged ⏳
- Outback: oil ✅ (Jun 2026), brakes 🔴 overdue, rear brake pads staged ✅, rotors needed, CEL monitoring

## Blocked
- Google Calendar auth (INC-006): OAuth client disabled by Google — fix via Cloud Console when ready
- Tacoma/Outback service day: waiting for good weather weekend; diffs/brakes/rotors to stage

## Next steps
1. Order WRX filters (15208AA170, qty 3) — 0 in stock
2. Order Outback rear rotors — pads staged, rotors still needed
3. Fix Google OAuth client (Cloud Console, Aaron's action)
4. Cadence: Aaron reports completed service → Pawl runs cadence-update silently
5. Tacoma service day: oil + diffs + brakes + rotation (parts staged)

## Resume instructions (after compaction)
1. Read SOUL.md, USER.md, MEMORY.md
2. Read this file
3. Read memory/2026-02-28.md for full session detail
4. Key tools: bin/cadence-check, bin/cadence-update, bin/travel-detect
5. Vehicle service logging rule: in AGENTS.md — run cadence-update silently when Aaron reports a completed service
