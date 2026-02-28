# Notification Routing

The right information through the right channel at the right time.

## The problem

Most agents dump everything into one stream — a morning briefing, a chat reply, a log. That's fine when the volume is low. As agents get more capable and track more things, the stream becomes noise. Important alerts get buried. Low-urgency updates interrupt high-focus moments.

Notification routing is the primitive that keeps signal clean as capability grows.

## Three channels

### Briefing (scheduled, batched)
- **When:** Fixed schedule (e.g., morning)
- **What:** Time-anchored context — weather, calendar, daily summary
- **Rule:** Only include things that are relevant *today by schedule*
- **Not for:** Event-driven alerts, maintenance reminders, background status

### Alert (event-driven, direct)
- **When:** Something crosses a threshold
- **What:** A single item that needs attention
- **Rule:** Send once per event. Don't repeat unless overdue and unresolved.
- **Not for:** Batched summaries, scheduled updates

### Digest (periodic summary)
- **When:** Weekly or on demand
- **What:** Everything coming up in the next window (e.g., Cadence items due in 30 days)
- **Rule:** On demand by default; scheduled only if the human opts in
- **Not for:** Urgent or time-sensitive items

## Routing rules

| Signal type | Channel | Frequency |
|-------------|---------|-----------|
| Weather, calendar | Briefing | Daily |
| Cadence approaching | Alert | Once per approach cycle |
| Cadence overdue | Alert | Once, then weekly nudge |
| System health issue | Alert | Immediately |
| Cost summary | Digest | Weekly (Friday review) |
| Capability unlock | Alert | On unlock |
| Cadence overview | Digest | On demand |

## Implementation pattern

Before sending any notification, ask:
1. Is this scheduled context? → Briefing
2. Is this an event that crossed a threshold? → Alert
3. Is this a summary of things to know? → Digest
4. Has this already been sent for this event cycle? → Skip

## Silence is a feature

A well-routed system is mostly quiet. The absence of alerts is confirmation that everything is on track. Humans should be able to go days without hearing from the agent and trust that silence means all clear.
