# The Incident Loop

The incident loop is how Ratchet turns failures into permanent improvements.

Most agents patch symptoms. They fix the immediate error, move on, and encounter the same class of problem again later. The incident loop breaks this cycle by treating every failure as a specimen — something to be examined, classified, and addressed at the root before the fix ships.

## The loop

```
Failure occurs
    ↓
Log the incident — before fixing anything
    ↓
Fix the immediate symptom
    ↓
Root cause analysis — what class of problem is this?
    ↓
Prevention tasks — address the class, not just the instance
    ↓
Prevention ships during a heartbeat
    ↓
Incident closed — the ratchet clicks forward
```

**Finding a bug is good news. Logging it is how you stop repeating it.**

## Why log first?

The order matters. Logging before fixing forces the agent to capture the blast radius and root cause while the evidence is fresh. Post-hoc documentation gets rationalized; real-time logging captures what actually happened.

## The incident record

Each incident produces a structured file with:

- **What happened** — timeline, first signal, full description
- **Root cause** — not the symptom, the underlying class of failure
- **Blast radius** — what was affected, for how long
- **Why it wasn't caught sooner** — the gap in monitoring or process
- **Prevention tasks** — concrete actions that address the root cause class
- **Status** — open, in progress, resolved

## Prevention tasks as first-class work

Prevention tasks are not suggestions. They execute autonomously during heartbeats:

- P1 prevention tasks run immediately
- P2/P3 tasks queue in the backlog
- No incident is "resolved" until prevention tasks are complete

This is the difference between patching a bug and fixing the class of bug.

## Incident classes

Incidents are grouped by class, not just instance. If the same class of incident recurs, that's a signal that the prevention task wasn't effective — the root cause wasn't actually addressed. The weekly review tracks recurrence by class.

Examples of classes:
- `parallel-execution` — agent deferred background work instead of spawning immediately
- `zombie-process` — stale process held a port after service restart
- `external-data-injection` — untrusted content influenced agent behavior
- `context-loss` — decision made without reading relevant memory files

## What "resolved" means

An incident is resolved when:
1. The immediate symptom is fixed
2. All prevention tasks are closed
3. The root cause class is documented
4. A recurrence would be caught earlier next time

A bug fixed without logging is a missed opportunity. A bug caught, logged, and prevented is a click of the ratchet.

---

*Part of the [Ratchet framework](https://github.com/ratchet-framework/Ratchet) — the reliability layer for AI agents.*
