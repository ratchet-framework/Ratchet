# CURRENT.md — What Pawl Is Building Right Now

## Session: 2026-03-01
**Status:** Epic 2 (Comms Queue + Trust Enforcement) shipped. Epic 3 (Behavioral Consistency) shipped. Guardrails active.

## Epic 2: Comms Queue + Trust Tier Enforcement — SHIPPED ✅

### What was built (sub-agent: epic-2-comms-queue)
- [x] **`bin/classify-audience`** — audience classifier. 11/11 smoke tests passing. Defaults to `external-unknown` (fail-safe). Public repos always external-unknown.
- [x] **`workspace/comms/`** — directory structure (`queue/`, `sent/`, `rejected/`). Draft JSON format documented in `comms/README.md`.
- [x] **`bin/comms-send`** — execute approved comms from queue. Gates: commsQueueEnabled check, approved status check, audience classification. Logs to `comms/audit.jsonl`.
- [x] **`bin/trust-check`** — evaluates all regression triggers from trust.json regressionRules. Reads incident files, counts P1/P2 by class and recency. JSON output + `--summary` mode.
- [x] **`bin/metrics-collect` updated** — added `weeks_since_last_incident`, `incident_severity_distribution` (trailing 4 weeks), `trust_tier_readiness` (boolean).
- [x] **`trust.json` updated** — added `regressionRules` block (5 triggers), `commsQueueEnabled: false`, `t3Phase: 1`.
- [x] **`capabilities.json` updated** — split `github` → `github-own-repos` (T2) + `github-external` (T3). Added `comms-queue` and `audience-classification` capabilities.

### Notable finding from trust-check run
- `p2Any3in4weeks` trigger is **LIVE** — 3 P2 incidents in last 4 weeks. Would trigger tier drop if `--apply` is run.
- `patternSystemic` also triggered. These are real signals from INC-005, INC-007, INC-009.
- Aaron should review before running `trust-check --apply`.



## Epic 3: Behavioral Consistency — SHIPPED ✅

### What was built (sub-agent: epic-3-guardrails)
- [x] **`guardrails.json`** — 9 guardrails derived from INC-001 through INC-009 (4 hard, 5 soft)
- [x] **`bin/preflight-check`** — keyword matching against guardrails, JSON output, exit code by severity
- [x] **`bin/pause-and-ask`** — queues actions to pending-actions.json, sends Telegram to Aaron with approve/cancel framing
- [x] **`bin/comms-review`** — approve/deny pending actions, timeout handling, audit log
- [x] **`bin/session-start`** — now injects compact guardrails summary (up to 5 lines) at session start

### How it works
- Before any high-risk action: `python3 bin/preflight-check "action description"` → JSON with matched rules
- To pause for approval: `python3 bin/pause-and-ask --action "..." --trigger "GR-003" --context "..." --severity destructive`
- Aaron approves/denies via: `python3 bin/comms-review <id> approve`
- All sessions now surface active guardrails automatically at startup

---

## Session: 2026-02-28 (Complete)
**Status:** All major work shipped. System stable. Ready for Aaron's return.

## What shipped today

### Core Framework Releases
- [x] **Ratchet Memory Phase 1** — LLM extraction + LLM retrieval (51 facts, proven)
- [x] **Ratchet Memory Phase 2** — Lifecycle scoring, decay, contradiction detection
- [x] **Ratchet Memory Phase 3** — Semantic embeddings + cosine similarity (TF-IDF fallback)
- [x] **Ratchet Memory Phase 4** — Workspace indexing, pattern detection, /insights page
- [x] **Compaction test** — Session continuity proven end-to-end

### Infrastructure & Operations
- [x] **Orchestration architecture** — Discord + worker droplet design doc + GitHub issues (#20-22)
- [x] **Worker droplet automation** — bin/provision-worker (idempotent, 15 min, one-command setup)
- [x] **Discord setup guide** — complete step-by-step (ratchet/docs/discord-setup.md)
- [x] **State of Pawl** — Opus deep analysis (incident patterns, T3 prognosis, honest advice)

### Product & Visibility
- [x] **Mission Control Memory Facts page** (/facts) — browse 51 facts with search, filters, importance visualization
- [x] **Mission Control /insights page** — pattern clusters, risk factors, recommendations
- [x] **getratchet.dev redesign** — hero rewrite, "how it works" loop, live stats, Opus quote, comparison table, prior art
- [x] **Reference implementations** — all 4 memory scripts published to GitHub

### Incident Resolution
- [x] **INC-007 remediated** — PROCESS.md parallel execution rule + metrics recurrence detection

### Documentation & Assets
- [x] **6 new concept docs** — adaptive-memory.md (full 3-phase + Phase 4), orchestration-architecture.md, discord-setup.md, state-of-pawl-2026-02-28.md, etc.
- [x] **Part pricing research** — order-links.md with direct links (WRX filters, Outback rotors)
- [x] **Return briefing** — memory/2026-02-28-return-briefing.md summarizing the evening's work

## Metrics
- **GitHub:** 12+ commits, 4 new pages (Memory /facts, /insights, updated nav), getratchet.dev redesigned
- **Memory system:** 51 facts extracted, 5 permanent-tier, avg importance 0.76
- **Capabilities:** 20 → 21 unlocked (34 total)
- **Incidents:** 7 total, INC-007 resolved, all prevention tasks complete
- **Patterns detected:** 7 incidents cluster around "repeated class + external comms," missing review gates (86%), time pressure (71%)

## Open — Needs Aaron
1. **Discord server setup** — create server, provide bot token (30 min)
2. **Part orders** — WRX filters (qty 3, links ready), Outback rotors (qty 2, links ready)
3. **Google OAuth re-auth** — when ready (not urgent)

## System Status
- All services: healthy
- New incidents: 0 (last 60 min)
- Cadence: all clear
- Publish verification: all verified
- Watchdog health: ✅ OK

## Epic 1: Mechanical Gates — SHIPPED ✅

### What was built (sub-agent: epic-1-mechanical-gates, 2026-03-01)

**Gate 1: Public repo content gate (extended)**
- Pre-commit hook now scans file CONTENT for private workspace references: MEMORY.md, SECURITY.md, THREAT-MODEL.md, trust.json, incidents/INC-, /memory/YYYY-MM
- Also blocks the droplet's public IP (64.225.15.45) in addition to RFC-1918 ranges
- Mirrored all new content checks to `.github/workflows/check-private-files.yml`
- Tested: commit blocked when file contains "MEMORY.md" reference ✅

**Gate 2: Parallel execution audit**
- New `bin/parallel-audit` — reads session .jsonl logs, detects inline research/analysis patterns
  - Thresholds: 3+ web calls, 5+ reads, 15+ tool calls without user input
  - Falls back to self-report prompt if logs unavailable
- Integrated into `bin/pre-compaction` (section 10) — runs at every compaction
- Violation state saved to `memory/parallel-audit-state.json`
- `bin/session-start` injects warning when previous session had violations
- Tested: detects 9 violations in known heavy session ✅

**Gate 3: Security review audit**
- Added to `bin/pre-compaction` (section 11)
- Detects new `bin/` or `ratchet/` files since last commit
- Warns if `## Security review` or "No sensitive data" not in CURRENT.md
- Tested: fires for `bin/crashloop-alert` (new file without review marker) ✅

## Security review

Epic 1 mechanical gates:
- Touch: session logs (read-only), git staged files (read-only), CURRENT.md (read), state file (write to memory/)
- Expose: stdout only, no network calls, no secrets
- External input: staged file content scanned via regex — no exec, no shell injection
- Execute: git commands via subprocess with no user-controlled strings in shell invocations
- Blast radius: low — worst case is false-positive block or missed violation. No data exfiltration risk.

## Next Steps (Priority Order)
1. **Discord setup** — high value, Aaron-initiated, ~30 min
2. **Part orders** — at Aaron's discretion (links ready in memory/order-links.md)
3. **Phase 5: Proactive learning** — auto-suggest improvements based on pattern analysis (future)
4. **Phase 6: Multi-agent orchestration** — dispatch sub-agents to address pattern recommendations (future)

## Resume Instructions
1. Run `python3 workspace/bin/session-start` to restore context
2. Check `/facts` and `/insights` pages in Mission Control (new)
3. Read return briefing: `memory/2026-02-28-return-briefing.md`
4. Review State of Pawl analysis: `ratchet/docs/state-of-pawl-2026-02-28.md`
5. Decide on Discord setup

## Session Notes
- 7+ hour session spanning compaction test, three parallel Memory phases, orchestration design, full infrastructure automation, product redesigns, and deep pattern analysis
- Autonomous work (while Aaron played D&D): 4 parallel sub-agents built and shipped simultaneously
- All work tested, committed, pushed to GitHub
- System remained stable throughout (0 new incidents)
- Code quality: all features have testing, documentation, integration with existing systems

## The Day In Numbers
- **51** facts extracted and stored
- **79** workspace documents indexed
- **21** capabilities unlocked (from 20)
- **7** incidents analyzed, patterns synthesized
- **4** major builds shipped while Aaron was away
- **12+** commits to GitHub
- **0** new incidents
- **1** compaction test passed

---

*Ready for Aaron's return. Everything tested, documented, and shipped.* 🔩
