# CURRENT.md — What Pawl Is Building Right Now

This file is committed to GitHub at the end of every session and updated by heartbeats.
It is the single source of truth for in-flight work. If context compacts, start here.

## Active session
**Date:** 2026-02-28
**Status:** Session complete — Aaron asleep

## What shipped tonight

### Mission Control mobile UX (complete)
- [x] Sidebar → hamburger drawer (MobileShell component)
- [x] Dashboard, Cron, System, Tasks, Documents, Memories — all MobileShell applied
- [x] Tasks: drill-to-detail with MEMORY.md context + line numbers
- [x] Documents: full list restored, tap to read
- [x] Auto-refresh (60s) on documents, memories, tasks pages
- [x] GitHub Issues #6 + #7 closed

### Ratchet framework
- [x] Self-documenting builds: `bin/screenshot-commit` — auto screenshots + GALLERY.md
- [x] All 6 Mission Control pages documented in docs/screenshots/
- [x] README reframed as engineering project (removed "conventions not code")
- [x] Session continuity: CURRENT.md live in repo
- [x] GitHub Issues #6, #7 closed; #8-10 open
- [x] Capabilities: 26/33 unlocked

## Security review (required before next build)

All future capabilities must pass the security gate in AGENTS.md before code is written.
THREAT-MODEL.md now has a "Proposed Capabilities" queue — new ideas go there first.

Next items cleared:
- Travel detection (Issue #9): cleared with mitigations (calendar titles untrusted, Aaron confirms context.json changes)
- Web content fetching (Issue #10): cleared with mitigations (isolated sessions, untrusted delimiters, no autonomous action)

## Next steps (in order)
1. Cadence data: Aaron to provide vehicle mileage + last service dates (Issue #8)
2. Travel detection automation (Issue #9)
3. Security: prompt injection defense for web content (Issue #10)
4. Add getratchet.dev/gallery page pulling from docs/GALLERY.md
5. Wire screenshot-commit into heartbeat for periodic Mission Control documentation

## Key files
- `bin/screenshot-commit` — screenshot + commit to docs/screenshots/
- `bin/unlock-capability` — now auto-screenshots on unlock
- `ratchet/docs/GALLERY.md` — visual build history
- `ratchet/docs/screenshots/` — 12 screenshots committed (6 pages × mobile + desktop)
- `second-brain/src/components/MobileShell.tsx` — reusable mobile wrapper

## Resume instructions (after compaction)
1. Read MEMORY.md
2. Read this file
3. Read memory/2026-02-28.md
4. Everything is in good shape — no broken state, no in-flight code changes
5. Next task: Cadence data from Aaron (Issue #8)
