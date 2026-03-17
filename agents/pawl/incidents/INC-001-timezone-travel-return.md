ID: INC-001
Date: 2026-02-27
Reported by: Alex
Severity: P2
Status: RESOLVED

## Summary
Cron jobs created during a two-week international trip retained the destination timezone after the user returned home, causing reminders to fire 6 hours early.

## Root cause
Cron jobs inherit timezone context from the time of creation. No process existed to audit or re-evaluate timezone-sensitive configurations when the user's location changes. There was also no return-from-travel checklist or trigger of any kind.

## Blast radius
All time-sensitive cron jobs were affected:
- Morning briefing: fired at 2:30 AM local time (intended 8:30 AM)
- Wake-up reminder: fired at 4:30 AM local time (intended 9:30 AM) — already delivered, could not be recalled
- get-ready-reminder: was misconfigured for 5:15 AM — caught and fixed before firing
- leave-now-reminder: was misconfigured for 5:35 AM — caught and fixed before firing
- Briefing content referenced trip destination weather and location — wrong after return

## Immediate fixes applied
- All recurring crons: timezone updated to home timezone
- All time-sensitive one-shot reminders: rescheduled to correct local times
- Briefing prompt updated: location, weather city, and units corrected
- `context.json` created to serve as authoritative location/timezone state going forward

## Prevention tasks
- [x] Create `context.json` as authoritative source for current location, timezone, and preferences
- [x] Add travel return protocol to MEMORY.md: on return from any trip, immediately audit all cron jobs
- [x] Add intent verification checklist to MEMORY.md: before creating time-sensitive crons, verify timezone matches context.json
- [x] Update HEARTBEAT.md: check BACKLOG.md and open incidents on every cycle
- [x] Add to AGENTS.md: always read context.json before creating time-sensitive tasks

## Lessons
- "Fixed" means the class of problem is addressed, not just the instance
- Time-sensitive configurations are location-dependent by nature; verify at creation and on location change
- A travel return is a high-risk moment for stale configuration — treat it as a trigger for a config audit
- Unit preferences and location context must be enforced at the prompt level, not assumed
- The prevention system (context.json + travel return protocol) was built same-day from this incident
