# Orchestration Architecture

> **Status:** Design document — February 2026  
> **Problem:** Channel noise + compute isolation as Pawl's autonomy increases  
> **Decision required:** Discord routing layer? Second droplet for worker isolation?

---

## Problem Statement

Pawl is increasingly capable. That creates two infrastructure gaps:

### 1. Channel Noise
Everything flows through one Telegram stream: conversation, heartbeat OKs, sub-agent results, briefings, alerts, cron output. Aaron sees all of it. As autonomy increases, the noise-to-signal ratio degrades. Routing discipline (see `notification-routing.md`) helps at the application layer, but the channel itself is a bottleneck — it's a single undifferentiated pipe.

### 2. Compute Isolation
Sub-agents run in the same process space as the main conversation session. Long-running autonomous tasks (research, weekly review synthesis, publishing) consume context window from the main session. There's no way to "fire and forget" truly isolated work — everything is entangled.

---

## Option A: Discord as Routing Layer

### What it enables
Discord supports multiple named channels in a server. Instead of all output going to one Telegram chat, different categories of Pawl output can be routed to different channels — visible only to Aaron, organized, and searchable.

### Proposed server structure

```
Pawl HQ (Discord Server)
├── 📋 #briefings          — Morning briefings, weekly reviews
├── 🚨 #alerts             — Threshold crossings, incidents, service outages
├── 🤖 #sub-agent-results  — Sub-agent completion reports (non-urgent)
├── 🔧 #system             — Heartbeat OKs, cron logs, health checks
├── 📝 #memory-updates     — When Pawl updates MEMORY.md, CURRENT.md
└── 💬 #chat               — Reserved: optional second conversation channel
```

**Permissions:** Single-user server. Aaron is owner, Pawl is a bot with write access to all channels. No other members needed.

### Routing rules

| Signal type | Channel |
|------------|---------|
| Morning briefing | #briefings |
| Weekly review | #briefings |
| Incident detected | #alerts |
| Service outage | #alerts |
| Sub-agent complete (no action needed) | #sub-agent-results |
| Heartbeat OK | #system |
| Cron output | #system |
| MEMORY.md / CURRENT.md updates | #memory-updates |
| Anything requiring Aaron's response | **Telegram** (stays primary) |

**Key principle:** Telegram remains the human-in-the-loop channel. Discord absorbs structured, lower-urgency output. Aaron only needs to act on Telegram; Discord is ambient awareness.

### What Discord does that Telegram can't

| Capability | Discord | Telegram |
|-----------|---------|----------|
| Named channels (routing) | ✅ Multiple | ❌ One chat per conversation |
| Message threads | ✅ Per-message threads | ❌ Limited |
| Pinned messages per channel | ✅ | ❌ Bot-pinned only |
| Searchable history by channel | ✅ | ⚠️ Global search only |
| Channel-specific notification settings | ✅ | ❌ |
| Embeds / rich formatting | ✅ Cards, fields | ⚠️ Markdown only |
| Slash commands | ✅ Native | ⚠️ Command workaround |
| Webhook posting (no bot session needed) | ✅ Trivial | ❌ Requires bot |

### OpenClaw config changes needed

OpenClaw supports Discord as a channel plugin. To route specific outputs to specific Discord channels:

1. **Create Discord bot** — Discord Developer Portal → New Application → Bot → copy token
2. **Add bot to server** — OAuth2 URL with `bot` scope, `Send Messages` + `Embed Links` permissions
3. **Configure OpenClaw** — add Discord plugin with bot token + server ID
4. **Per-message routing** — in Pawl's code, use `message(action="send", target="#sub-agent-results", channel="discord")` instead of defaulting to Telegram
5. **Telegram stays default** — only override for non-urgent categories; anything requiring Aaron's response routes to Telegram as before

The routing logic lives in AGENTS.md (the `Telegram Routing Discipline` section). Discord just adds additional targets to that table.

### Tradeoffs

**Pros:**
- Zero additional infrastructure cost (Discord is free)
- Immediate — can be set up in an afternoon
- Retroactively searchable by channel
- Aaron can mute #system and #sub-agent-results without losing alerts
- Embeds make sub-agent output much more readable

**Cons:**
- Another app for Aaron to check (though low urgency = low pressure)
- OpenClaw Discord plugin may need configuration testing
- Routing discipline requires code changes to produce correct `channel=` targets
- Discord's bot API has occasional rate limits and outages (minor)
- Adds a dependency: Discord bot token must be kept valid

**Verdict:** High value, low cost. Not mutually exclusive with a second droplet.

---

## Option B: Second DigitalOcean Droplet (Worker Instance)

### What it enables
A dedicated worker droplet runs long-running sub-agents and background tasks in isolation from the main conversation session. The main droplet stays lean and responsive; the worker handles compute-heavy autonomous work.

### What runs on the worker

**Worker droplet responsibilities:**
- Long-running sub-agent tasks (research, synthesis, publishing)
- Cron jobs that are currently burdening the main session
- Weekly review generation
- GitHub commit/push workflows
- Any task that Aaron doesn't need to watch in real-time

**Main droplet responsibilities (stays):**
- Live Telegram conversation (Pawl's "consciousness")
- Heartbeat checks
- Orchestration / spawning workers
- Memory management (MEMORY.md, CURRENT.md)
- Short-lived, interactive sub-agents

### Coordination model

The git-based CURRENT.md pattern already works. Extend it:

```
Coordination layer (git repo — already exists):
├── CURRENT.md           — Main session state, what's in-flight
├── worker/QUEUE.md      — Tasks queued for worker (main writes, worker reads)
├── worker/RESULTS/      — Worker writes results here, main reads
└── worker/HEARTBEAT.md  — Worker liveness (last ping timestamp)
```

**Flow:**
1. Main session writes task to `worker/QUEUE.md` + pushes to git
2. Worker droplet polls git (every 60s) or uses a webhook trigger
3. Worker claims task, runs it (potentially hours)
4. Worker writes result to `worker/RESULTS/<task-id>.md` + pushes
5. Main session reads result on next heartbeat, routes to Discord/Telegram as appropriate

**Alternative: lightweight API** — Worker exposes a simple FastAPI endpoint. Main POSTs a task, worker runs it async, result is POSTed back to a webhook URL. More real-time but adds an HTTP server to the worker.

**Recommendation:** Start with git-based (zero new infrastructure), graduate to API if latency becomes an issue.

### Cost

| Tier | Specs | Monthly |
|------|-------|---------|
| Basic (1 vCPU, 512MB) | Lightest possible | ~$4/mo |
| Basic (1 vCPU, 1GB) | Comfortable for Node.js + OpenClaw | ~$6/mo |
| Basic (2 vCPU, 2GB) | Parallel sub-agents | ~$12/mo |
| Basic (2 vCPU, 4GB) | Heavy workloads | ~$24/mo |

**Recommended starting tier:** **1 vCPU, 2GB RAM at ~$12/mo**. OpenClaw itself requires ~512MB at idle; sub-agents spike. 2GB gives headroom without overprovisioning.

**Total added cost:** ~$12/month.

### Deployment / provisioning plan

1. **Snapshot current droplet** — baseline before adding complexity
2. **Create worker droplet** — same region, Basic 2GB, Ubuntu 24.04
3. **Install OpenClaw** — same version as main, worker-only config
4. **Clone Ratchet workspace** — `git clone` the workspace repo (read/write access via PAT already in secrets)
5. **Configure worker role** — `ROLE=worker` env var; worker config disables Telegram in, enables task polling
6. **Deploy git polling script** — `bin/worker-poll` (new tool): reads QUEUE.md, claims tasks, runs them, writes results
7. **Test with a safe task** — weekly review generation as first worker task
8. **Document as Ratchet primitive** — `worker-droplet.md`

### Tradeoffs

**Pros:**
- True compute isolation — long tasks don't affect main session context
- Main session stays fast and responsive
- Can be destroyed/rebuilt without affecting Pawl's "personality"
- Scales independently — upgrade worker without touching main
- Failure isolation — worker crash doesn't kill Pawl's conversation

**Cons:**
- +$12/month ongoing cost
- Coordination latency (git poll = up to 60s delay)
- Two systems to maintain, monitor, update
- Secrets must be replicated to worker (security surface)
- OpenClaw worker mode may need config tuning

---

## Recommendation

### Phase 1 (Now): Discord routing — 1 day of work, $0/month

Discord gives the highest immediate value for the lowest cost and effort. The channel noise problem is worse *today* than the compute isolation problem. Aaron is seeing sub-agent results and system messages that he shouldn't need to act on. Discord fixes that immediately.

**What to build:**
1. Create Pawl HQ Discord server
2. Add Discord bot + configure OpenClaw Discord plugin
3. Update AGENTS.md routing table with Discord targets
4. Update sub-agent result handling to route to `#sub-agent-results`
5. Route heartbeat OKs and cron output to `#system`

**Minimal viable change:** Even without full Discord integration, routing discipline changes alone (NO_REPLY for non-actionable sub-agent results) reduce Telegram noise immediately. Discord then adds the *ambient visibility* layer.

### Phase 2 (1-2 months): Worker droplet — when sub-agent volume justifies it

The compute isolation problem becomes acute when Pawl is regularly spawning 3+ concurrent sub-agents or running tasks that take >30 minutes. We're not there yet. When the weekly review synthesis or publishing pipeline starts consuming noticeable context, that's the trigger.

**Decision trigger:** If any single autonomous task causes a session compaction or noticeably slows conversation response → spin up the worker.

**What to build:**
- Worker droplet provisioning
- `bin/worker-poll` script
- `worker/QUEUE.md` coordination protocol
- Document as Ratchet primitive

### 6-Month Architecture

```
                    Aaron
                      │
              ┌───────┴────────┐
              │                │
           Telegram          Discord
         (actions needed)  (ambient)
              │            ├── #briefings
              │            ├── #alerts
              │            ├── #sub-agent-results
              │            └── #system
              │
         Main Droplet (robo-server-1)
         ├── Pawl main session
         ├── Heartbeat / coordination
         ├── Short sub-agents (<5 min)
         └── git push → workspace repo
                            │
                     Worker Droplet
                     ├── Long sub-agents
                     ├── Weekly review
                     ├── Publishing pipeline
                     └── git push → results
```

**What this looks like in practice:**
- Aaron's Telegram is clean: only things that need his attention
- Discord is Pawl's "ops dashboard" — always there, never urgent
- Long autonomous work runs on the worker; results surface in Discord when done
- Ratchet documents both as primitives: `channel-routing.md` + `worker-isolation.md`

---

---

## Worker Droplet — Provisioning

> **Status:** Scripts built — February 2026

### One-command setup

```bash
export DO_API_TOKEN=your_digitalocean_api_token
workspace/bin/provision-worker
```

The script is idempotent — safe to run twice. It won't create a second droplet if `pawl-worker-1` already exists.

**What it does:**
1. Validates DO API token and SSH key from your DigitalOcean account
2. Creates `pawl-worker-1` in nyc3 (`s-1vcpu-2gb`, Ubuntu 22.04)
3. Waits for droplet to become active and SSH-ready
4. Installs: Node.js 22, OpenClaw, git, python3
5. Configures OpenClaw in headless/worker mode (no Telegram, cron-only)
6. Clones the ratchet workspace repo (if GitHub credentials are present)
7. Creates a systemd service (`openclaw-worker`) — not auto-started, for your review
8. Adds a heartbeat cron that writes to `worker/HEARTBEAT.md` every 5 minutes
9. Prints a migration checklist for cron jobs

**Prerequisites Aaron needs to provide:**
- `DO_API_TOKEN` — DigitalOcean personal access token (Manage → API)
- SSH key uploaded to DigitalOcean (account → Security)
- Optional: `/root/.openclaw/secrets/pawl-github.env` with `GITHUB_TOKEN`, `GITHUB_USER`, `GITHUB_EMAIL`, `GITHUB_REPO` for automatic workspace clone

### Cost

**$12/month** (`s-1vcpu-2gb` in nyc3).

| Main droplet | Worker droplet |
|---|---|
| Live Telegram conversation | Long-running sub-agents |
| Heartbeat / coordination | Weekly review generation |
| Short-lived interactive sub-agents | GitHub commit/push workflows |
| Memory management (MEMORY.md, CURRENT.md) | Research and synthesis tasks |
| Orchestration / spawning | Publishing pipeline |

### Check worker health

```bash
DO_API_TOKEN=<token> workspace/bin/worker-status
```

Reports: droplet status, SSH reachability, OpenClaw version, systemd service state, active crontab, heartbeat freshness, task queue depth.

### Coordination model

See **Option B** above for the full design. Short version:

- Main session writes tasks to `worker/QUEUE.md`, pushes to git
- Worker polls git, claims tasks, writes results to `worker/RESULTS/<task-id>.md`
- Heartbeat written every 5 min to `worker/HEARTBEAT.md`
- Main session reads results on next heartbeat cycle

---

## GitHub Issues

See issues filed in ratchet-framework/Ratchet for implementation tracking.

### Epic: Mission Control (milestone 3)
These belong under Mission Control — the capability that gives the operator visibility and control over what the agent is doing, without being overwhelmed by it.

**Issues to create:**
1. **Channel routing layer** — Discord integration + routing rules (Phase 1)
2. **Worker droplet isolation** — second instance + git coordination protocol (Phase 2)
3. **Ratchet primitive: multi-channel routing** — document the pattern for any Ratchet deployment
