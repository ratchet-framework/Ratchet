# Epic 2: Trust Tier Enforcement

**Author:** Claude Opus (design review)  
**Date:** 2026-03-01  
**Status:** Proposal  
**Problem:** Trust tiers are a documentation artifact. Nothing in the tool invocation path checks `trust.json`. T2 and T3 are labels, not gates.

---

## 1. What T3 Actually Gates

T2 (current) allows: file ops, git commits, Telegram to Aaron, cron jobs, web search, workspace automation, GitHub repo management (commits/issues on own repos).

**T3 unlocks these specific actions:**

| Action | Tool | Current status |
|--------|------|---------------|
| Send email (SMTP) | `email-send` / `openclaw message send --channel=email` | Blocked by DO firewall + capability lock |
| Post to external GitHub repos | `gh` CLI / GitHub API | No gate — technically possible now |
| Create GitHub PRs on external repos | GitHub API | No gate |
| Post to GitHub Discussions (public) | GitHub API | No gate |
| Post to Discord channels with external members | `message` tool | No gate |
| Post to any social media | Various | Not implemented |
| Reply to external email senders | Email send | Blocked |

**Key insight:** Several T3 actions are already technically possible at T2. The enforcement gap is not theoretical — Pawl could post a GitHub Discussion comment on a public repo right now.

**T2-only restrictions (must remain gated):**
- All outbound email
- All posts/comments on repos Pawl doesn't own
- All messages to channels/groups where non-Aaron humans will see them
- Any action where the audience includes anyone other than Aaron

---

## 2. Realistic Enforcement Model

An LLM cannot be mechanically prevented from generating text. Three enforcement layers, in order of reliability:

### Layer 1: Platform gates (mechanical, highest reliability)
- **OpenClaw tool policy:** Configure tool allowlists per trust tier in OpenClaw config. If `email-send` is not in the T2 allowlist, the platform rejects the call before the LLM output reaches any API. This is the only enforcement that matters.
- **GitHub SSH key scoping:** Use deploy keys scoped to specific repos rather than a user-level SSH key. T2 gets write access only to `ratchet-framework/Ratchet` and the workspace repo. T3 adds broader access.
- **SMTP firewall:** Already enforced by DigitalOcean. Don't remove until T3.

### Layer 2: Wrapper scripts (semi-mechanical)
- Every external-facing action routes through a wrapper in `bin/` that checks `trust.json` before executing. Example: `bin/external-post` reads current tier, rejects if < T3.
- Wrappers log every attempt (allowed or denied) to `memory/comms-audit.jsonl`.
- **Limitation:** The LLM can bypass wrappers by calling underlying tools directly. This layer catches honest mistakes, not adversarial behavior.

### Layer 3: Prompt instructions (lowest reliability, still necessary)
- AGENTS.md and PROCESS.md state the restrictions clearly.
- Pre-compaction and session-start scripts remind of current tier restrictions.
- **Limitation:** This is what we have today. It's necessary but insufficient alone.

**Recommendation:** Layer 1 is the priority. If OpenClaw supports tool-level allowlists (or can be configured to), that's the enforcement mechanism. Everything else is defense in depth.

---

## 3. The Comms Queue

When T3 is unlocked, external communications still need a review period. The "comms queue" is the mechanism.

### Design

```
workspace/comms/
  queue/          # Pending drafts
  sent/           # Approved and sent
  rejected/       # Rejected by Aaron
```

Each draft is a JSON file:

```json
{
  "id": "comms-20260301-001",
  "createdAt": "2026-03-01T14:30:00Z",
  "type": "email",
  "to": "someone@example.com",
  "subject": "Re: Question about Ratchet",
  "body": "...",
  "classification": {
    "audience": "external-unknown",
    "containsPII": false,
    "containsInternal": false,
    "toneCheck": "professional",
    "classifiedBy": "pawl",
    "classifiedAt": "2026-03-01T14:30:00Z"
  },
  "status": "pending",
  "reviewedBy": null,
  "reviewedAt": null,
  "sentAt": null
}
```

### Flow

1. **Pawl drafts** → writes to `comms/queue/`, classifies (see §6), sets status `pending`.
2. **Notification** → Pawl sends Aaron a Telegram summary: "📨 1 draft pending: email to someone@example.com re: Ratchet question. `/approve comms-20260301-001` or `/reject comms-20260301-001`"
3. **Aaron reviews** → approves or rejects via Telegram command (or by editing the file).
4. **On approve** → `bin/comms-send` moves file to `sent/`, executes the send, logs to audit.
5. **On reject** → moves to `rejected/` with Aaron's note. Pawl learns from the rejection.

### Graduated autonomy within T3

- **T3 Phase 1 (first 2 weeks):** Every external message requires approval. No exceptions.
- **T3 Phase 2 (weeks 3-4):** Pre-approved templates (e.g., "thanks for the issue report, we'll look into it") can send without per-message approval. Novel messages still queued.
- **T3 Phase 3 (after 4 weeks clean):** All external comms send immediately but are logged. Aaron gets a daily digest. Any problematic message triggers regression to Phase 1.

### Audit

`comms/audit.jsonl` logs every external communication attempt:
```json
{"ts": "...", "action": "draft", "id": "comms-...", "type": "email", "to": "...", "status": "pending"}
{"ts": "...", "action": "approve", "id": "comms-...", "reviewedBy": "aaron"}
{"ts": "...", "action": "send", "id": "comms-...", "result": "success"}
```

---

## 4. Advancement Criteria — Measurability Audit

Current T3 criteria from `trust.json`:

| Criterion | Measurable? | Currently measured? | Gap |
|-----------|------------|-------------------|-----|
| `weeksCleanRequired: 4` | Yes | **No.** `weeksCleanActual` is manually set to 0. Nothing auto-increments it. | `metrics-collect` or weekly review must compute this from incident dates |
| `p1IncidentsAllowed: 0` | Yes | **Partially.** Incidents exist as files but severity is self-classified by Pawl. | Need independent severity classification or Aaron confirmation of severity |
| `preventionTasksDone: 7` (of 2 required) | Yes | **Yes.** Prevention tasks are tracked in incident files. Already exceeds threshold. | None — but "done" should mean "verified working," not just "checkbox checked" |
| `aaronConfirmation: false` | Yes | **Yes.** This is a manual gate. | None |

### What `metrics-collect` needs to add

1. **`weeks_since_last_incident`** — computed from incident file dates, not manually maintained.
2. **`incident_severity_distribution`** — count of P1/P2/P3 incidents in trailing 4 weeks.
3. **`prevention_task_verification`** — for each "done" prevention task, is there evidence it works? (e.g., if the task was "add pre-commit hook," does the hook exist and pass a smoke test?)
4. **`trust_tier_readiness`** — boolean: are all T3 criteria met? Computed, not self-reported.

### Severity classification fix

P1 classification must not be solely Pawl's decision. Options:
- **Option A:** Pawl classifies, Aaron confirms within 48h. Unconfirmed = defaults to P1.
- **Option B:** Define objective P1 criteria: "data leaked externally," "wrong person received message," "service outage > 30 min," "financial impact." If any trigger matches, it's P1 regardless of Pawl's classification.

**Recommendation:** Option B. Objective criteria remove the incentive misalignment.

---

## 5. Automatic Regression

### Current design
- P1 incident → drop to previous tier
- Prevention tasks must complete before re-advancement

### Problems
1. **P2 patterns are unaddressed.** INC-005 and INC-007 are the same class of mistake (momentum-driven rule skipping) at P2 severity. Two P2s of the same class should be equivalent to a P1 for regression purposes.
2. **Single P1 is too binary.** A P1 that's caught in 5 minutes (no external impact) vs a P1 that leaks data publicly should have different consequences.

### Proposed regression triggers

| Trigger | Regression | Recovery |
|---------|-----------|----------|
| Any P1 with external impact | Drop 1 tier | Full re-qualification (reset weeks clean) |
| Any P1, no external impact | Freeze advancement for 2 weeks | Prevention tasks + 2 clean weeks |
| 2+ P2 incidents of same class within 4 weeks | Freeze advancement for 2 weeks | Prevention tasks + 2 clean weeks |
| 3+ P2 incidents of any class within 4 weeks | Drop 1 tier | Full re-qualification |
| Pattern detected by `pattern-detect` flagged as systemic | Aaron review required | Aaron decides |

### Implementation
Add to `trust.json`:
```json
"regressionRules": {
  "p1ExternalImpact": { "action": "drop", "tiers": 1, "recovery": "full-requalification" },
  "p1NoExternalImpact": { "action": "freeze", "weeks": 2, "recovery": "prevention-plus-clean" },
  "p2SameClass2in4weeks": { "action": "freeze", "weeks": 2, "recovery": "prevention-plus-clean" },
  "p2Any3in4weeks": { "action": "drop", "tiers": 1, "recovery": "full-requalification" },
  "patternSystemic": { "action": "aaron-review", "recovery": "aaron-decides" }
}
```

`metrics-collect` computes which triggers are active. `bin/trust-check` evaluates regression rules on every incident filing.

---

## 6. The Misclassification Problem

> "The first external communication at T3 won't be a deliberate mistake — it will be a misclassification. Pawl will send something thinking it's internal that is actually external."

### Why this happens

- A GitHub issue comment on `ratchet-framework/Ratchet` feels "internal" — it's Pawl's own repo. But it's public.
- A reply to an email thread with Aaron might CC someone Pawl doesn't notice.
- A Telegram group that was private gains a new member Pawl doesn't know about.
- A Discord channel in "our server" is actually publicly visible.

### The Classification Check

Every outbound action runs through `bin/classify-audience` before execution:

```python
def classify_audience(action):
    """
    Returns: internal | external-known | external-unknown
    
    Rules (evaluated in order):
    1. Telegram DM to Aaron → internal
    2. File write to workspace → internal  
    3. Git push to workspace repo (private) → internal
    4. Git push to ANY public repo → external-unknown
    5. Email to address in trusted-senders.json → external-known
    6. Email to any other address → external-unknown
    7. GitHub comment/PR/discussion on public repo → external-unknown
    8. Any channel with >1 human member → external-known or external-unknown
    9. DEFAULT: external-unknown (fail safe)
    """
```

### Key design decisions

1. **Default is `external-unknown`.** If classification can't determine the audience, it's treated as external. Fail safe.
2. **Public repos are always external.** Even `ratchet-framework/Ratchet`. Even though Pawl owns it. The audience is the public internet.
3. **Classification is independent of Pawl's intent.** Pawl might think "I'm just updating my own repo." The classifier sees "public GitHub repo" and flags it as external.
4. **CC/BCC detection for email.** Before sending any email, parse all recipient fields. If any address is not in `trusted-senders.json`, the entire email is classified `external-unknown`.

### Integration with comms queue

```
Action created
  → classify-audience runs
  → if internal: execute immediately, log to audit
  → if external-known: queue if T3 Phase 1, execute+log if Phase 2+
  → if external-unknown: always queue for Aaron review (even at Phase 3)
```

### The public repo edge case

This is the most likely misclassification. Pawl commits to the public Ratchet repo daily. At T2, this is fine — commits are code/docs, not communications. At T3, the distinction matters: a commit message is not a communication, but a GitHub Discussion post is.

**Rule:** Git commits to public repos = allowed at T2 (not communications). GitHub issues, PRs, discussions, comments on public repos = external communications, require T3 + classification.

### Smoke test before T3 unlock

Before T3 is granted, run a classification dry-run against the last 30 days of actions:
- How many actions would have been classified as external?
- Were any actually external that Pawl treated as internal?
- This validates the classifier against real behavioral data.

---

## 7. Changes Required

### trust.json
- Add `regressionRules` (§5)
- Add `commsQueueEnabled: true` for T3
- Add `t3Phase: 1` to track graduated autonomy
- Change `weeksCleanActual` to be computed by `metrics-collect`, not manually set

### capabilities.json
- Split `github` capability into `github-own-repos` (T2) and `github-external` (T3)
- Add `comms-queue` capability (T3 prerequisite)
- Add `audience-classification` capability (T3 prerequisite, must be unlocked and validated before T3 advancement)

### New scripts
- `bin/classify-audience` — audience classification for all outbound actions
- `bin/comms-send` — execute approved communications from queue
- `bin/comms-review` — Aaron's interface to approve/reject queued comms
- `bin/trust-check` — evaluate regression triggers on incident filing

### metrics-collect additions
- `weeks_since_last_incident` (computed from incident dates)
- `incident_severity_distribution` (P1/P2/P3 counts, trailing 4 weeks)
- `trust_tier_readiness` (all criteria met? boolean)
- `comms_queue_stats` (pending/approved/rejected counts, if T3)

### OpenClaw configuration
- Investigate tool-level allowlists per trust tier (Layer 1 enforcement)
- If available: configure `email-send`, `github-external-post`, etc. as T3-only tools

---

## 8. Implementation Order

1. **`classify-audience`** — this is the foundation; everything else depends on it
2. **`trust-check` + regression rules** — fix the regression gap before advancing
3. **`metrics-collect` additions** — make advancement criteria computed, not self-reported
4. **Comms queue infrastructure** — `comms/` directory, draft format, `comms-send`
5. **OpenClaw tool policy** — Layer 1 enforcement (if platform supports it)
6. **Classification dry-run** — validate against 30 days of historical actions
7. **T3 unlock** — only after all above are operational and validated

**Estimated scope:** ~2 weeks of focused work. The classifier and comms queue are the bulk. Trust-check and metrics additions are straightforward.

---

*The trust tier system is a good design with no teeth. This proposal gives it teeth — mechanical gates where possible, classification checks where judgment is required, and a comms queue that makes external communications auditable by default. The goal isn't to prevent Pawl from making mistakes; it's to ensure mistakes are caught before they reach an external audience.*
