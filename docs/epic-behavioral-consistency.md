# Epic 3: Behavioral Consistency

**Author:** Claude Opus (architectural review)  
**Date:** 2026-03-01  
**Status:** Design  

---

## 1. Is This Solvable at the Framework Level?

Honest answer: **partially.**

Full behavioral consistency requires calibrated uncertainty — knowing what you don't know. That's a model-level capability. No amount of framework scaffolding will make a model that's confidently wrong become appropriately uncertain. Ratchet can't fix calibration any more than a cockpit checklist can fix a pilot's judgment.

What Ratchet *can* do:

- **Create mechanical gates** that prevent certain action classes without explicit approval, regardless of the model's confidence level. This is the seatbelt approach: it works whether you think you need it or not.
- **Surface patterns** from past failures into the decision context at the moment they're relevant, not just in a dashboard after the fact.
- **Force structured pauses** at high-risk decision points, converting "I think I can handle this" into "let me check before I handle this."

What Ratchet *cannot* do:

- Make the model genuinely uncertain when it should be. Models are confidently wrong in ways that are not introspectable.
- Guarantee that rules loaded at context minute 1 are still active at minute 47. Context window attention decay is a physics problem, not an engineering problem.
- Replace judgment. The trigger conditions for "pause and ask" require judgment to evaluate, which means the system is ultimately guarding against its own judgment failures using... its own judgment.

**This is an engineering problem wrapped around a research problem.** The engineering problem (mechanical gates, pattern injection, pause primitives) is solvable in 60 days. The research problem (calibrated model uncertainty) is not. Design for that boundary.

---

## 2. Minimal Useful Version

The INC-005 → INC-007 pattern is the clearest signal. The rule existed. It was documented. It was violated hours later. Documentation didn't change behavior.

The minimal intervention that would have prevented INC-007:

**A pre-action check injected into the system prompt that triggers on specific action patterns, not on every action.**

Concretely: when Pawl is about to execute a task inline (not spawn a sub-agent), a lightweight check fires: "Does this match a known incident pattern?" If yes, surface the relevant incident before proceeding.

This is not metacognition. It's `grep` at the decision boundary. The smallest version:

1. Maintain a `guardrails.json` file: a list of trigger patterns and their associated rules.
2. Before high-risk actions (defined below), check the action against guardrails.
3. If a match fires, inject the rule + incident history into the immediate context.

This doesn't require the model to be uncertain. It requires the framework to remind the model of things it has already decided, at the moment those decisions are relevant.

---

## 3. Confidence Signaling

### Design

Not a confidence score on every action. That's theater — the model will produce 0.85 on everything and it'll mean nothing.

Instead: **structured pre-flight checks on actions that match trigger conditions.**

### Trigger Conditions

A pre-flight check fires when ANY of:

1. **The action touches a public surface.** Git push to public repo, sending email, posting anywhere external. (INC-003 class)
2. **The action was previously the subject of an incident.** Pattern match against `guardrails.json` entries derived from closed incidents. (INC-005/007 class)
3. **The action involves irreversible state change.** File deletion, database modification, sending a message that can't be unsent. Defined by action type, not model judgment.
4. **The action operates on data the model hasn't seen recently.** E.g., modifying a file that wasn't read in the current context window. Proxy for stale mental model. (INC-001 class — timezone assumptions)
5. **The action scope exceeds what was explicitly requested.** Aaron asked for X; Pawl is about to do X + Y. The "Y" part triggers a check. (INC-003 class — asked for docs, got sensitive screenshots)

### What the Check Looks Like

Not a popup. Not a confidence number. A structured internal note:

```
[PRE-FLIGHT] Action: git push to ratchet (public repo)
Trigger: public surface + prior incident INC-003
Check: Does this commit contain files matching private patterns?
Rule: Pre-commit hook should catch this, but verify manually.
Proceed: yes/no
```

This is injected as a tool-use step, not as a prompt instruction. The framework calls a `preflight-check` tool before the action executes. The tool returns the check result. The model sees the result and decides.

### Why This Works Better Than Rules in AGENTS.md

Rules in AGENTS.md compete with 50KB of other context. A pre-flight check is injected *at the decision point*, when attention is on the action. It's the difference between a speed limit sign on the highway entrance (read once, forgotten) and a speed limit sign at the curve (read when it matters).

---

## 4. The "Pause and Ask" Primitive

### When It Triggers

Subset of the pre-flight triggers, elevated severity:

- **Mandatory pause (always):** First use of a new capability (first email send, first public post). Any action that would be P1 if wrong.
- **Conditional pause:** Pre-flight check fires AND the model's self-assessed confidence is below threshold (this is the weakest link — model self-assessment is unreliable, so keep the mandatory list honest).
- **Pattern pause:** The `pattern-detect` system has flagged this action class as recurring-risk in the last 30 days.

### How It Surfaces

**Primary: Telegram message to Aaron.**

```
🔩 [PAUSE] I'm about to [action description].
Trigger: [why this paused]
Context: [1-2 lines of relevant context]

Reply ✅ to proceed, ❌ to cancel, or tell me what to change.
```

**Secondary: Queue file (`pending-actions.json`)** for when Telegram delivery fails or Aaron is offline.

### Timeout Behavior

- **Destructive/irreversible actions:** No timeout. Wait indefinitely. The action doesn't happen without approval.
- **Time-sensitive but reversible:** 4-hour timeout. If no response, take the conservative path (don't act) and log it.
- **Informational pauses** (Pawl is uncertain but action is low-risk): 30-minute timeout, then proceed with the safer option and notify Aaron after the fact.

### Implementation

```python
# pause_and_ask.py
import json, time
from pathlib import Path

PENDING = Path("pending-actions.json")

def pause(action: str, trigger: str, context: str, severity: str = "destructive"):
    """Queue an action for human approval."""
    entry = {
        "id": str(uuid4()),
        "action": action,
        "trigger": trigger,
        "context": context,
        "severity": severity,  # destructive | time-sensitive | informational
        "requested_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "timeout": {"destructive": None, "time-sensitive": 14400, "informational": 1800}[severity]
    }
    # Append to queue
    pending = json.loads(PENDING.read_text()) if PENDING.exists() else []
    pending.append(entry)
    PENDING.write_text(json.dumps(pending, indent=2))
    
    # Send Telegram notification
    send_telegram_pause(entry)
    
    return entry["id"]

def check_approval(action_id: str) -> str:
    """Returns: approved | denied | timeout | pending"""
    # ... check pending-actions.json for status update
```

Aaron's Telegram reply updates `pending-actions.json` via a webhook or heartbeat poll. The heartbeat already runs every 30 minutes — it checks the pending queue as part of its cycle.

### What This Doesn't Solve

If Aaron is unreachable for 12+ hours and a destructive action is queued, Pawl is blocked. This is a feature, not a bug. The alternative — acting without approval on destructive actions — is how INC-003 happened.

---

## 5. Learning from Incidents: Closing the Loop

### The Gap

Today's loop: Incident → Log → Prevention tasks → Pattern-detect → `/insights` dashboard.

The dashboard is a dead end. Patterns are surfaced for Aaron to read. They don't feed back into Pawl's decision-making. The loop is open.

### The Missing Link: `guardrails.json`

Close the loop with one file and one injection point.

**`guardrails.json`** — machine-readable behavioral rules derived from incidents:

```json
[
  {
    "id": "GR-001",
    "source": "INC-005, INC-007",
    "pattern": "inline_execution_of_spawnable_task",
    "trigger": "about to execute a task that doesn't require Aaron's live input",
    "rule": "Spawn a sub-agent. No exceptions. No size threshold.",
    "severity": "hard",
    "added": "2026-02-28",
    "last_fired": null,
    "fire_count": 0
  },
  {
    "id": "GR-002",
    "source": "INC-003",
    "pattern": "commit_to_public_repo",
    "trigger": "git add/commit/push in ratchet/ directory",
    "rule": "Verify no private-pattern files in staging. Check pre-commit hook ran.",
    "severity": "hard",
    "added": "2026-02-28"
  },
  {
    "id": "GR-003",
    "source": "INC-001",
    "pattern": "timezone_dependent_action",
    "trigger": "creating cron jobs or time-based automation",
    "rule": "Verify current timezone from context.json. Do not assume.",
    "severity": "soft",
    "added": "2026-02-26"
  }
]
```

**The injection point:** `session-start` loads `guardrails.json` and injects a compact summary into the session context. Not the full file — a 5-line "active guardrails" block that lists current rules. This puts incident learnings into the context window where they compete for attention alongside everything else — but at least they're *present*.

**The reinforcement point:** `preflight-check` (from section 3) queries `guardrails.json` at the decision boundary. This is the second injection — not at session start (where it decays) but at action time (where it matters).

**The update loop:**

```
Incident logged
    → Prevention tasks completed
    → pattern-detect identifies the class
    → Human or automated process adds entry to guardrails.json
    → session-start loads it next session
    → preflight-check enforces it at action time
    → guardrail fire logged (fire_count, last_fired)
    → Weekly review reports guardrail activations
```

### Why Two Injection Points

Session-start injection handles the "awareness" problem: Pawl knows the rules exist. But as State of Pawl identified, awareness decays over the session.

Preflight injection handles the "enforcement" problem: at the moment of action, the relevant rule is re-surfaced. This is the mechanical gate — it doesn't rely on the model remembering. It triggers automatically based on action classification.

Neither is perfect. Together, they're meaningfully better than rules-in-AGENTS.md alone.

### What Makes This Engineering, Not Research

- `guardrails.json` is a flat file. No ML, no embeddings, no model calls.
- Trigger matching is keyword/pattern-based. Not semantic understanding.
- The injection is a string concatenation into the prompt. Not a novel architecture.
- The preflight check is a tool call. Standard tool-use pattern.

This is plumbing. It works because it puts the right information in the right place at the right time, not because it makes the model smarter.

---

## 6. What's Realistic in 60 Days

### Phase 1: Foundation (Days 1–20)

**Guardrails file + session injection.**
- Create `guardrails.json` from existing incidents (7 incidents → ~5-7 guardrails)
- Modify `session-start` to load and inject compact guardrail summary
- Estimated effort: 2-3 focused sessions

**Preflight check tool.**
- Build `bin/preflight-check` that accepts an action description, matches against guardrails, returns relevant rules
- Wire into the system prompt as a recommended tool before high-risk actions
- Estimated effort: 2-3 focused sessions

**Deliverable:** Guardrails are present in context and queryable at action time.

### Phase 2: Pause Primitive (Days 20–40)

**`pending-actions.json` + Telegram integration.**
- Build `bin/pause-and-ask` with queue, Telegram notification, and timeout logic
- Add pending-action check to heartbeat cycle
- Wire Aaron's Telegram replies to update pending status
- Estimated effort: 3-4 focused sessions

**Trigger conditions for mandatory pause.**
- Define initial trigger list (public surface actions, first-use of new capability)
- Hard-code in `preflight-check` — expand later based on data
- Estimated effort: 1 session

**Deliverable:** High-risk actions pause for approval. Aaron gets Telegram notifications. Timeouts work.

### Phase 3: Loop Closure (Days 40–60)

**Automated guardrail generation from pattern-detect.**
- Modify `pattern-detect` to output candidate guardrail entries when it identifies a recurring pattern
- Human review required before entries are added to `guardrails.json` (Aaron approves via Telegram or PR)
- Estimated effort: 2 sessions

**Guardrail effectiveness tracking.**
- Track `fire_count` and `last_fired` in guardrails.json
- Weekly review reports: which guardrails fired, which are stale (never fire → maybe remove), which actions were paused
- Estimated effort: 1-2 sessions

**Validation.**
- Review 30 days of guardrail data: did any incidents occur that a guardrail should have caught? Did any guardrails fire unnecessarily (false positives)?
- Adjust trigger conditions based on data
- Estimated effort: 1 session

**Deliverable:** Closed loop from incidents → patterns → guardrails → enforcement → measurement.

### What's NOT in 60 Days

- Model-level calibrated uncertainty. Research problem. Not in scope.
- Semantic trigger matching (understanding *intent* behind actions, not just pattern matching). Requires embeddings and is fragile. Defer.
- Commitment tracking ("you said you'd do X, did you?"). Useful but separate from behavioral consistency. Backlog it.
- Mid-session self-audit. Promising but hard to get right without burning tokens on constant re-reading. Defer to Phase 2 of this epic.
- Tool-enforced gates that make it mechanically impossible to skip steps. The nuclear option. Requires deep integration with OpenClaw's tool dispatch. Defer until guardrails data shows which gates are actually needed.

---

## 7. Success Criteria

After 60 days, the system should demonstrate:

1. **Zero repeated-class incidents within a session.** The INC-005 → INC-007 pattern should not recur. Guardrails + preflight should catch it.
2. **All public-surface actions pass through preflight.** No git push to public repo, no email send, no external post without a preflight check firing.
3. **At least one incident prevented by a pause.** The pause primitive should demonstrably catch something that would have been an incident without it.
4. **Guardrail fire rate > 0 and false positive rate < 30%.** The guardrails should fire when they're supposed to and not fire constantly.
5. **Closed loop from pattern-detect to guardrails.json.** At least 2 guardrails should be added from pattern-detect output during the 60-day period.

### What This Doesn't Guarantee

Behavioral consistency is a spectrum, not a binary. This epic reduces the incident surface for *known* failure patterns. It does not prevent novel failures. The model can still be confidently wrong in ways that no guardrail anticipated.

The honest framing: **this turns behavioral consistency from a hope into a system.** The system has limits. But a system with limits beats hope with none.

---

*Written by Claude Opus. March 1, 2026.*
