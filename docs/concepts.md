# Ratchet — Core Concepts

## The loop

Ratchet is built around a single feedback loop:

```
Issue surfaces → Postmortem → Prevention tasks → Backlog → Autonomous execution → Memory update → Loop
```

Every component serves this loop. The loop is what makes the agent improve.

## Memory vs state

**MEMORY.md** is long-term curated knowledge — the distilled essence of everything the agent has learned. It's maintained by the agent, updated when something worth remembering happens, pruned when information becomes stale. Think of it like a person's long-term memory: not everything, just what matters.

**Daily logs** (`memory/YYYY-MM-DD.md`) are raw session notes — what happened, what changed, what needs follow-up. The agent writes these; the weekly review synthesizes them into MEMORY.md.

**context.json** is authoritative state — things that should never be assumed. Location, timezone, preferences, units. Always checked before creating anything time-sensitive. Updated explicitly when state changes (travel, move, preference change).

## The incident loop

When something goes wrong — whether the human reports it or the agent notices — it becomes an incident:

1. **Log it** — create `incidents/INC-NNN-*.md` with root cause, blast radius, prevention tasks
2. **Fix the symptom** — immediately, in the same session
3. **Queue prevention** — add prevention tasks to BACKLOG.md
4. **Execute prevention** — autonomously, during heartbeats or dedicated runs
5. **Close the incident** — when all prevention tasks are complete

The key principle: "fixed" means the *class* of problem is addressed, not just the instance.

## The backlog

The backlog is the agent's self-directed work queue. Three priority levels:

- **P1** — do immediately, next heartbeat
- **P2** — this week
- **P3** — when bandwidth allows

Items enter the backlog from:
- Incident prevention tasks
- Gap audits (things the agent notices it can't do well)
- Strategic improvements (capabilities to build)

Items exit the backlog when they're done — moved to the Completed table with outcome noted.

## Autonomy tiers

Ratchet agents start conservative and expand their autonomy over time, as trust is earned through demonstrated reliability.

**Tier 1 (start here)**
- Internal work: read, write, organize files
- Run scheduled tasks and heartbeats
- Log incidents and queue prevention work
- Always ask before: sending external messages, spending money, making irreversible changes

**Tier 2 (earned)**
- Execute prevention tasks without prompting
- Make judgment calls on ambiguous internal decisions
- Proactively surface issues before the human notices

**Tier 3 (target)**
- Operate autonomously for extended periods
- Human interaction is strategic direction, not task management
- Weekly review is the primary sync point

The human defines the tier boundaries. They shift explicitly, not implicitly.

## Heartbeat

The heartbeat is a recurring check-in — typically every 30 minutes during active hours. It's the mechanism that drives autonomous work:

1. Check system health
2. Check for P1 backlog items → execute
3. Check for open incident prevention tasks → execute
4. Work through P2/P3 backlog items (one per heartbeat, non-quiet hours)
5. Report only if something needs human attention

During quiet hours (human asleep), heartbeat only alerts on urgent issues (system down, data loss risk, etc.).

## Weekly review

Every Friday (or configured day), the agent runs a structured self-review:

1. Read the week's daily logs
2. Read all open/in-progress incidents
3. Read the backlog — what got done, what's pending
4. Synthesize patterns and lessons → update MEMORY.md
5. Send a brief summary to the human

The weekly review is the primary mechanism for MEMORY.md staying current and for the human staying informed without being involved in day-to-day operations.

## Intent verification

Before creating anything time-sensitive (reminders, scheduled tasks, briefings), the agent runs a mental checklist:

- Timezone: matches the human's *current* location
- Units: matches the human's preferences (from context.json)
- Location references: correct city/region
- Time of day: makes sense in local time (5 AM is rarely right)
- Preferences: all applied

This prevents the entire class of problems where literal compliance misses actual intent.

## The ratchet metaphor

The pawl is the piece in a ratchet that locks each click in place and prevents backward movement.

In Ratchet, the pawl is the memory + incident system. Every problem that gets root-caused and prevented is a click. Every lesson added to MEMORY.md is a click. Every autonomy tier earned is a click. Nothing regresses because the prevention work actually gets done, and the memory actually persists.

The agent is always moving forward. The question is only how fast.
