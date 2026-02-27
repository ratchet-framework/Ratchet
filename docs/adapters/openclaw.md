# Ratchet — OpenClaw Adapter

[OpenClaw](https://openclaw.ai) is the reference platform for Ratchet. This document explains how to wire Ratchet's core components into an OpenClaw setup.

## Prerequisites

- OpenClaw installed and running (`openclaw gateway status`)
- A Telegram (or other channel) configured for your agent
- A workspace directory (default: `~/.openclaw/workspace`)

## File placement

Place the Ratchet template files in your OpenClaw workspace:

```
~/.openclaw/workspace/
├── MEMORY.md
├── BACKLOG.md
├── context.json
├── AGENTS.md          # OpenClaw agent instructions
├── SOUL.md            # Agent persona
├── HEARTBEAT.md       # Heartbeat behavior
├── incidents/
│   └── README.md
├── memory/
└── bin/
```

OpenClaw automatically loads `AGENTS.md`, `SOUL.md`, `MEMORY.md`, and `HEARTBEAT.md` as workspace context.

## Heartbeat

OpenClaw has a built-in heartbeat system. Configure your `HEARTBEAT.md` to include Ratchet's backlog and incident checks:

```markdown
## On each heartbeat

1. Check system health (services, watchdog endpoint)
2. Check BACKLOG.md for P1 items → execute immediately
3. Check incidents/ for open prevention tasks → execute if autonomous
4. Work one P2/P3 backlog item (non-quiet hours only)
5. If nothing needs attention: reply HEARTBEAT_OK (silent)
```

Set heartbeat frequency in your OpenClaw config. 30 minutes is a good starting point.

## Weekly review cron

Create a cron job for the weekly self-review:

```bash
openclaw cron add \
  --name "Weekly Self-Review" \
  --cron "0 17 * * 5" \
  --tz "America/New_York" \
  --session isolated \
  --model "anthropic/claude-sonnet-4-6" \
  --timeout-seconds 300 \
  --announce \
  --channel telegram \
  --to "YOUR_TELEGRAM_ID" \
  --message "$(cat path/to/weekly-review-prompt.md)"
```

See `template/prompts/weekly-review.md` for the full prompt.

## Morning briefing cron

```bash
openclaw cron add \
  --name "Morning Briefing" \
  --cron "0 7 * * *" \
  --tz "America/New_York" \
  --session isolated \
  --model "anthropic/claude-haiku-4-5" \
  --timeout-seconds 180 \
  --announce \
  --channel telegram \
  --to "YOUR_TELEGRAM_ID" \
  --message "$(cat path/to/morning-briefing-prompt.md)"
```

## context.json — intent verification

OpenClaw agents can read `context.json` before creating any time-sensitive cron or reminder. Add this to your `AGENTS.md`:

```markdown
## Before creating any reminder or cron job
Read `workspace/context.json`. Verify:
- Timezone matches `location.timezone`
- Units match `units.*` preferences
- Location references match `location.display`
```

## Model recommendations

| Task | Model | Reasoning |
|------|-------|-----------|
| Heartbeat checks | claude-haiku-4-5 | Fast, cheap, adequate for health checks |
| Morning briefing | claude-haiku-4-5 | Simple synthesis, low cost |
| Weekly review | claude-sonnet-4-6 | Needs reasoning and synthesis |
| Incident postmortem | claude-sonnet-4-6 | Root cause analysis benefits from stronger model |
| Strategic planning | claude-opus-4-6 | Reserve for complex, high-stakes reasoning |

## Notes

- Cron jobs in OpenClaw use IANA timezone strings (`America/New_York`, not `EST`)
- Always set `--tz` explicitly — do not rely on defaults
- **Isolated sessions cannot reach `127.0.0.1`** — isolated cron jobs run sandboxed; localhost resolves to the sandbox, not the host. Do not check local health endpoints from isolated sessions.
- Canary design: if a cron runs and returns a result, that itself proves the scheduler, agent execution, and delivery channel are all working. No health endpoint check needed.
- One-shot reminders: use `--delete-after-run` to auto-cleanup
