# CURRENT.md — What Pawl Is Building Right Now

This file is committed to GitHub at the end of every session and updated by heartbeats.
It is the single source of truth for in-flight work. If context compacts, start here.

## Active session
**Date:** 2026-02-28
**Status:** In progress

## What's in-flight

### Mission Control mobile UX
- [x] Sidebar → hamburger drawer
- [x] MobileShell component created
- [x] Dashboard, Cron, System pages updated
- [x] Tasks page wired to real API
- [ ] Documents page — MobileShell not yet applied
- [ ] Memories page — MobileShell not yet applied
- [ ] Auto-refresh (60s poll) on documents + memories pages

### Ratchet framework
- [x] Cost routing primitive + cost-log tool
- [x] Cadence primitive + cadence-check tool
- [x] Notification routing primitive
- [x] Capability dashboard live at getratchet.dev/dashboard.html
- [ ] Cadence data: needs Aaron's vehicle mileage + last service dates
- [ ] GitHub Issues: BACKLOG.md items not yet mirrored as Issues

## Next steps (in order)
1. Apply MobileShell to Documents page
2. Apply MobileShell to Memories page
3. Add auto-refresh to Mission Control
4. Mirror BACKLOG.md active items to GitHub Issues
5. Populate Cadence with vehicle data (needs Aaron)

## Key files being worked on
- `second-brain/src/app/documents/page.tsx`
- `second-brain/src/app/memories/page.tsx`
- `second-brain/src/components/MobileShell.tsx` (done)
- `ratchet/capabilities.json`

## Resume instructions (for next session after compaction)
1. Read MEMORY.md → understand full context
2. Read this file → understand what's in-flight
3. Read memory/2026-02-28.md → today's session detail
4. Continue with "Next steps" above
5. Use `verify-ui` + `screenshot-local.js` to check Mission Control before/after any UI change
