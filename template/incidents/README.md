# Incident Log

Every time something breaks, falls short, or surfaces a gap — whether the human reports it or the agent notices it — it gets logged here as a postmortem.

## Purpose

- Build institutional memory about failure modes
- Track prevention work to completion
- Identify recurring patterns over time
- Create accountability: "fixed" means root cause addressed, not just symptom patched

## File naming

`INC-NNN-short-description.md`

Sequential. Never delete. Mark resolved, not removed.

## Severity levels

- **P1** — actively causing harm or significant disruption right now
- **P2** — meaningfully degraded experience; human noticed or would have soon
- **P3** — minor gap; caught proactively or low impact

## Status values

- `OPEN` — identified, not yet fully resolved
- `IN PROGRESS` — immediate fix done; prevention work underway
- `RESOLVED` — all prevention tasks complete, MEMORY.md updated

## Template

```
ID: INC-NNN
Date: YYYY-MM-DD
Reported by: [Human name] | Self
Severity: P1 | P2 | P3
Status: OPEN | IN PROGRESS | RESOLVED

## Summary
One sentence: what went wrong.

## Root cause
Why did this happen? Not "what happened" — why.

## Blast radius
What else was or could be affected by the same root cause?

## Immediate fixes
What was done right now to address the symptom?

## Prevention tasks
- [ ] Task 1
- [ ] Task 2

## Lessons
What goes into MEMORY.md or process docs to prevent recurrence class-wide?
```
