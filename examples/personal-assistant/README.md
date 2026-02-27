# Pawl — Reference Implementation

Pawl is the personal assistant agent that runs on Ratchet. This directory contains sanitized artifacts from real usage — real incidents, real backlog items, real memory patterns.

## Setup

- **Platform:** OpenClaw
- **Primary channel:** Telegram
- **Models:** claude-haiku-4-5 (heartbeat, briefing), claude-sonnet-4-6 (weekly review, incidents)
- **Heartbeat:** every 30 minutes, 8 AM – 9 PM local time

## What Pawl does

- **Morning briefing** (7:00 AM daily) — weather, news, system status, proposed tasks
- **Heartbeat monitoring** (every 30 min) — system health, backlog execution, incident follow-up
- **Reminders** — appointments, travel, recurring tasks
- **Weekly self-review** (Fridays 5 PM) — incident synthesis, memory update, summary to human
- **Autonomous improvement** — works through the backlog between sessions

## Key files

- [`incidents/INC-001-timezone-travel-return.md`](incidents/INC-001-timezone-travel-return.md) — first incident; shows the full prevention loop

## Notes

All personal information (name, location, employer, contacts) has been replaced with generic placeholders. Timing, process, and structure reflect actual usage.
