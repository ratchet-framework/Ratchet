# Epic 1: Mechanical Gates

**Author:** Claude Opus (engineering review)  
**Date:** 2026-03-01  
**Status:** Proposal  
**Relates to:** INC-003, INC-005, INC-007, engineering-review-2026-03-01.md

---

## Problem Statement

Every process rule in PROCESS.md and AGENTS.md is advisory. Advisory rules compete with task momentum and lose. Evidence:

- **INC-005 + INC-007:** "Spawn a sub-agent for background work" — violated twice in one day, hours apart, after being documented as a rule. Prevention tasks were completed between incidents. Documentation didn't prevent recurrence.
- **INC-003:** "Don't leak private data to public surfaces" — violated when screenshot-commit ran against internal pages. Post-incident fix was mechanical (URL allowlist, pre-commit hook). The mechanical fix works; the advisory rule didn't.

The pattern: documentation-based rules fail under momentum. Mechanical enforcement works. Build more mechanical enforcement.

---

## What "Enforced" Actually Means in an LLM Context

Let's be honest about the enforcement spectrum:

| Level | Mechanism | Reliability | Example |
|-------|-----------|-------------|---------|
| **Hard gate** | Code that blocks action | ~100% | Pre-commit hook rejecting private files |
| **Audit gate** | Code that detects + alerts after the fact | ~95% | Session-end check counting inline research tasks |
| **Prompt gate** | Injected context that reminds at decision point | ~70-80% | System prompt instruction with examples |
| **Documentation** | Rules in files the model reads at session start | ~40-60% | PROCESS.md rules |

An LLM cannot be mechanically prevented from generating text inline instead of spawning a sub-agent — the decision happens inside the generation. But we can:

1. **Detect violations after the fact** (audit gate) and surface them immediately
2. **Inject reminders at the decision point** (prompt gate) to raise compliance
3. **Block downstream effects** (hard gate) for actions that flow through tools

The INC-003 fix (pre-commit hook) is a hard gate — it works at the tool level. The parallel execution problem needs an audit gate — we can't prevent inline work, but we can detect it happened and flag it before the session ends.

---

## Gate Rankings

Ranked by `P(preventing real incident) × implementation cost`:

| Rank | Gate | Incident Class | Type | Effort |
|------|------|---------------|------|--------|
| 1 | **Public repo content gate** | INC-003 (data leak) | Hard | 2h |
| 2 | **Parallel execution audit** | INC-005/007 (promise-breaking) | Audit | 4h |
| 3 | **External comms queue** | T3 future (wrong email sent) | Hard | 6h |
| 4 | **Security review gate** | Unreviewed capability ships | Audit | 2h |
| 5 | **Fact schema validation** | Silent memory corruption | Hard | 3h |

---

## Gate 1: Public Repo Content Gate (Hard Gate)

**Already partially built.** INC-003 produced a pre-commit hook and GitHub Action. Extend it.

### Current state
- Pre-commit hook in `.git/hooks/pre-commit` blocks known private filenames
- GitHub Action enforces on push/PR
- `.ratchet-public` allowlist for overrides

### What's missing
- **No content scanning.** Hook checks filenames, not file content. A renamed `MEMORY.md` or a new file containing personal data passes through.
- **No cross-repo confusion protection.** A sub-agent in the wrong `cwd` could `git add -A` in the ratchet repo and pick up workspace files symlinked or copied in.

### Implementation

**File:** `ratchet/.git/hooks/pre-commit` (extend existing)

Add content-level checks:

```bash
# After existing filename checks...

# Content scan: reject files containing private markers
for file in $(git diff --cached --name-only --diff-filter=ACM); do
    # Check for private content markers
    if git show ":$file" | grep -qiE '(MEMORY\.md|SECURITY\.md|THREAT-MODEL\.md|trust\.json|incidents/INC-|/memory/[0-9]{4}-[0-9]{2})' 2>/dev/null; then
        echo "❌ BLOCKED: '$file' contains references to private workspace content"
        exit 1
    fi
    # Check for email addresses (simple pattern)
    if git show ":$file" | grep -qE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' 2>/dev/null; then
        echo "❌ BLOCKED: '$file' contains email addresses"
        exit 1
    fi
done
```

**Test:** Create a test file in ratchet containing "MEMORY.md" reference, try to commit, verify rejection.

**Effort:** 2 hours (extend hook + mirror to GitHub Action + test).

---

## Gate 2: Parallel Execution Audit (Audit Gate)

This is the big one. INC-005 + INC-007 = same class, twice, same day, with documentation in between.

### Why a hard gate is impossible

The decision to run work inline vs. spawn a sub-agent happens inside text generation. There's no tool call to intercept — the absence of a `sessions_spawn` call IS the violation. You can't block a non-event.

### The mechanism: detect-and-flag

**What we can detect:** After a session (or mid-session at compaction), we can analyze the tool call history and identify patterns that look like inline research/analysis that should have been spawned.

**Signals that indicate an inline violation:**
1. `web_search` or `web_fetch` called 3+ times in sequence without user messages in between
2. `read` called on 5+ different files in sequence (research pattern)
3. Session duration > 10 minutes between user messages while tools were being called (long inline work)
4. Text generation > 2000 tokens between user messages that isn't a direct answer

### Implementation

**File:** `workspace/bin/parallel-audit`

```python
#!/usr/bin/env python3
"""
parallel-audit — Detect inline work that should have been spawned.

Reads the current session's tool call log and flags patterns that match
research/analysis work done inline instead of via sub-agent.

Exit code 0: clean
Exit code 1: violations detected (prints details)
"""

import json
import sys
import os
from datetime import datetime, timedelta

# Configurable thresholds
WEB_CALL_THRESHOLD = 3      # sequential web_search/web_fetch without user input
READ_CALL_THRESHOLD = 5      # sequential read calls without user input
TOOL_SEQUENCE_THRESHOLD = 6  # any tool calls in sequence without user input

def analyze_session_log(log_path):
    """Analyze a session log for parallel execution violations."""
    violations = []
    
    if not os.path.exists(log_path):
        return violations
    
    with open(log_path) as f:
        events = [json.loads(line) for line in f if line.strip()]
    
    # Walk through events, tracking tool calls between user messages
    tool_streak = []
    web_streak = 0
    read_streak = 0
    
    for event in events:
        if event.get("role") == "user":
            # User message resets streaks
            if web_streak >= WEB_CALL_THRESHOLD:
                violations.append({
                    "type": "inline_research",
                    "detail": f"{web_streak} sequential web calls without user input",
                    "tools": [t["name"] for t in tool_streak if t.get("name") in ("web_search", "web_fetch")]
                })
            if read_streak >= READ_CALL_THRESHOLD:
                violations.append({
                    "type": "inline_analysis",
                    "detail": f"{read_streak} sequential file reads without user input",
                    "tools": [t["name"] for t in tool_streak if t.get("name") == "read"]
                })
            if len(tool_streak) >= TOOL_SEQUENCE_THRESHOLD and web_streak < WEB_CALL_THRESHOLD and read_streak < READ_CALL_THRESHOLD:
                violations.append({
                    "type": "inline_work",
                    "detail": f"{len(tool_streak)} sequential tool calls without user input",
                    "tools": [t.get("name", "unknown") for t in tool_streak]
                })
            tool_streak = []
            web_streak = 0
            read_streak = 0
        elif event.get("role") == "tool" or event.get("type") == "tool_call":
            tool_name = event.get("name", "")
            tool_streak.append(event)
            if tool_name in ("web_search", "web_fetch"):
                web_streak += 1
            else:
                web_streak = 0
            if tool_name == "read":
                read_streak += 1
            else:
                read_streak = 0
    
    return violations

if __name__ == "__main__":
    log_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not log_path:
        print("Usage: parallel-audit <session-log-path>")
        sys.exit(2)
    
    violations = analyze_session_log(log_path)
    if violations:
        print(f"⚠️  PARALLEL EXECUTION VIOLATIONS: {len(violations)}")
        for v in violations:
            print(f"  • {v['type']}: {v['detail']}")
        sys.exit(1)
    else:
        print("✅ No parallel execution violations detected")
        sys.exit(0)
```

### Integration points

1. **`pre-compaction` script:** Run `parallel-audit` on the current session log. If violations detected, print a warning that gets included in the compaction summary. This creates a feedback loop — every compaction reminds Pawl of inline violations.

2. **Weekly metrics:** `metrics-collect` counts violations per week. Trend line shows whether the audit gate is working.

3. **Session-start injection:** At session start, if the previous session had violations, inject a one-line reminder: "⚠️ Last session had N parallel execution violations. Spawn sub-agents for research/analysis."

### What this does NOT do

It doesn't prevent inline work. It detects it after the fact and creates social pressure (the audit trail). This is the right level — a hard block would be worse than the disease (sometimes inline work IS correct, e.g., reading a single file to answer a question).

### The real question: can we access session tool logs?

**This is the implementation dependency.** OpenClaw's session log format and location need to be known. If session logs aren't accessible as structured data, this gate can't be built as described. 

**Fallback if logs aren't accessible:** The pre-compaction script asks Pawl to self-report: "List all research/analysis tasks you ran inline this session." Self-reporting is weaker than log analysis but still creates the audit habit. Combined with the injected session-start reminder, it's ~80% as effective.

**Effort:** 4 hours (script + integration into pre-compaction + session-start injection + testing). Add 2h if session log format needs reverse-engineering.

---

## Gate 3: External Comms Queue (Hard Gate — for T3)

When T3 unlocks, Pawl can draft and send external communications. This is the highest-stakes new capability. Design the gate before the capability exists.

### Mechanism: Draft Queue with Explicit Send

**Principle:** Pawl can draft freely. Sending requires explicit confirmation. The queue is the gate.

### Architecture

```
workspace/
  outbox/
    drafts/          ← Pawl writes here
      001-email-to-bob.json
      002-github-discussion.json
    sent/             ← Moved here after confirmed send
      ...
    rejected/         ← Moved here if Aaron rejects
      ...
```

**Draft format:**
```json
{
  "id": "001",
  "type": "email",
  "to": "bob@example.com",
  "subject": "Re: Project update",
  "body": "...",
  "drafted_at": "2026-03-15T10:30:00Z",
  "context": "Aaron asked me to follow up on the project status",
  "urgency": "normal",
  "status": "pending_review"
}
```

### How Aaron interacts

**Option A: Telegram inline** (recommended for Phase 1)
- Pawl drafts a message, saves to outbox, sends Aaron a Telegram summary:
  > 📤 **Draft ready:** Email to bob@example.com  
  > Subject: Re: Project update  
  > [Preview: first 200 chars]  
  > Reply "send", "edit", or "reject"
- Aaron's reply triggers the action
- This uses existing Telegram infrastructure, no new UI needed

**Option B: Mission Control page** (Phase 2)
- Outbox page shows all pending drafts
- Approve/edit/reject buttons
- Better for batches, worse for single messages

### The gate mechanism

**File:** `workspace/bin/send-external`

```python
#!/usr/bin/env python3
"""
send-external — The only path to send external communications.

Pawl MUST use this script to send any external message. The script:
1. Saves draft to outbox/drafts/
2. Notifies Aaron via Telegram
3. Waits for confirmation
4. Only sends on explicit "send" command

Direct use of email/social tools is blocked by prompt instruction
(soft gate) + post-session audit (audit gate).
"""
```

**The hard part:** Pawl could bypass the queue and call the email tool directly. This is the LLM enforcement problem — you can't mechanically prevent a tool call that the model has access to.

**Mitigation layers:**
1. **Prompt gate:** Session instructions say "ALL external comms go through `send-external`. Direct tool calls for email/social are violations."
2. **Audit gate:** Pre-compaction checks for direct email/social tool calls that didn't go through the queue. Flags them as violations.
3. **Hard gate (if OpenClaw supports it):** Configure tool access policies to require confirmation for email-send tools. This is the ideal but depends on platform capability.

### Trust-based vs. mechanically enforced

Honest assessment:
- **Draft creation → queue:** Mechanically enforced (script writes to disk)
- **Aaron's confirmation → send:** Mechanically enforced (script reads confirmation)  
- **Pawl always using the queue:** Trust-based, backed by audit gate
- **Content quality/tone:** Fully trust-based (no mechanical check for "wrong tone")

**Effort:** 6 hours (draft queue script + Telegram notification integration + send-on-confirm + audit check in pre-compaction).

---

## Gate 4: Security Review Audit (Audit Gate)

### Problem
The security gate in PROCESS.md says "answer these questions before writing code." Nothing checks this happened.

### Mechanism

**File:** Add to `pre-compaction` script:

```python
# Check: any new files in bin/ or ratchet/ without a security review marker
new_files = get_new_files_since_last_session()  # from git diff
bin_files = [f for f in new_files if f.startswith("bin/") or f.startswith("ratchet/")]
if bin_files:
    # Check CURRENT.md for security review section
    current = read_file("ratchet/CURRENT.md")
    if "## Security review" not in current and "No sensitive data" not in current:
        warn(f"New capability files {bin_files} committed without security review in CURRENT.md")
```

**Effort:** 2 hours.

---

## Phase 1: Minimal Viable Gates

Build these three. Everything else waits.

### 1. Extend public repo pre-commit hook (2h)
- Add content scanning to existing hook
- Mirror to GitHub Action
- **Test:** Try committing a file with email addresses → blocked

### 2. Parallel execution audit in pre-compaction (4h)
- Build `parallel-audit` script  
- Integrate into `pre-compaction`
- Add session-start reminder when previous session had violations
- **Test:** Run against a session log with known inline research → flags it

### 3. Security review check in pre-compaction (2h)
- Add new-capability detection to pre-compaction
- Flag missing security review
- **Test:** Commit a new `bin/` script without "Security review" in CURRENT.md → warning

**Total Phase 1 effort: ~8 hours**

### What Phase 1 does NOT include
- External comms queue (not needed until T3 — build when T3 is candidate)
- Hard blocks on tool calls (depends on OpenClaw platform capabilities we haven't explored)
- Real-time interception (too complex, too invasive, wrong ROI for now)

### Success criteria
- Zero INC-003-class incidents (data leak to public repo) — pre-commit hook catches it
- Parallel execution violations detected and reported — awareness drives behavior change
- New capabilities always have security review — or pre-compaction flags the gap

---

## What's Still Trust-Based (and That's OK)

Some things can't be mechanically enforced in an LLM system. Accept it:

1. **Quality of judgment** — when to spawn vs. answer inline for truly trivial things
2. **Tone and appropriateness** — no gate can catch "technically correct but contextually wrong"
3. **Incident severity classification** — Pawl classifies its own incidents (conflict of interest, but no practical alternative)
4. **Completeness of security reviews** — we can check one exists, not that it's thorough

The strategy: mechanically enforce what we can, audit what we can detect, and trust what we must. Each incident that gets through the trust layer gets a mechanical fix. The ratchet clicks forward.

---

## Implementation Order

1. **Week 1:** Gate 1 (pre-commit extension) + Gate 4 (security review audit)
2. **Week 2:** Gate 2 (parallel execution audit) — needs session log investigation
3. **When T3 is candidate:** Gate 3 (external comms queue)

---

*Gates don't make the system perfect. They make the same mistake harder to repeat. That's the ratchet.*
