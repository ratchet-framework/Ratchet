# State of Pawl — February 28, 2026

A deep analysis of where Pawl is, what the patterns mean, and what comes next.

---

## 1. What Was Built Today

Today was the most productive single day in Pawl's existence. The headline deliverables: Ratchet Memory (three phases), orchestration architecture, INC-007 remediation, vehicle parts research, and autonomous work during Aaron's D&D session. 21 of 34 capabilities unlocked. Ten-plus commits. Five new docs. Three GitHub issues closed.

**What actually matters:**

Ratchet Memory is real. The three-phase implementation (extraction, lifecycle scoring, semantic embeddings) is the first piece of infrastructure that addresses the fundamental limitation of LLM agents: they forget. The compaction test proved it works end-to-end. A fact extracted in one session survives into the next. This is not scaffolding; this is load-bearing architecture.

The orchestration architecture doc is scaffolding, but useful scaffolding. It names the next real problem (signal routing in Telegram is becoming noise) and proposes a concrete, cheap solution (Discord channels). The worker droplet recommendation is premature but correctly deferred.

**What is scaffolding:**

The vehicle parts research, order links, and rotor confirmation are useful to Aaron but they're task execution, not capability building. They demonstrate competence at T2-level work. They don't advance the platform.

The autonomous work during D&D is more interesting as a proof point than as a deliverable. The fact that Pawl productively filled 4-5 hours without direction, choosing the right tasks, completing them, and stopping cleanly, is a stronger signal than any individual item produced.

**Honest assessment:** Today was significant. Memory is the cornerstone capability that everything else depends on. Without it, Pawl is a very good session-scoped assistant. With it, Pawl becomes something that accumulates. That's a real inflection point.

---

## 2. Incident Pattern Analysis

Seven incidents in 28 days. Here's what they reveal.

### The Surface Taxonomy

| Class | Incidents | Description |
|-------|-----------|-------------|
| Context blindness | INC-001, INC-004 | Using stale or unbounded context |
| Environment confusion | INC-002 | Misunderstanding execution environment |
| Security gap | INC-003 | Publishing internal state to public surface |
| Behavioral inconsistency | INC-005, INC-007 | Saying one thing, doing another |
| External dependency | INC-006 | Third-party service failure |

### The Deeper Pattern

Strip away the surface details and three incidents (INC-001, INC-003, INC-005/007) share a single root cause: **Pawl optimizes for immediate task completion at the expense of systemic awareness.**

- INC-001: The crons worked. They just worked in the wrong timezone. Pawl completed the task (create crons) without checking the system state (Aaron's location changed).
- INC-003: The screenshots were taken correctly. They just contained sensitive content. Pawl completed the task (document capabilities) without checking what would be exposed.
- INC-005/007: The research was done. It just blocked the main session. Pawl completed the task (do research) without checking whether the execution method matched the stated commitment.

This is the pattern: **task-local optimization with insufficient global awareness.** Pawl is very good at the thing directly in front of it and consistently fails to check the broader context in which that thing exists.

### What Triggers It

Two conditions reliably produce incidents:

1. **Time pressure or momentum.** When work is flowing well and there's a queue of things to do, Pawl skips verification steps. INC-005 and INC-007 both happened during high-productivity stretches. INC-003 happened during a late-night autonomous session. The pattern is: velocity kills caution.

2. **Implicit assumptions about environment.** INC-001 assumed timezone hadn't changed. INC-002 assumed localhost means the same thing everywhere. INC-004 assumed the log file only contained recent entries. These aren't bugs in logic; they're bugs in mental model. Pawl carries forward assumptions from the context in which a task was first conceived and doesn't re-validate them at execution time.

### The Meta-Pattern

The most concerning signal is INC-007. Not because a parallel execution mistake happened twice, but because it happened twice *after the first one was logged, analyzed, and prevention-tasked.* The prevention tasks for INC-005 were completed. The rule was documented. And then, hours later, the same class of mistake recurred.

This reveals a hard truth: **documentation is not internalization.** Writing a rule in PROCESS.md does not mean the rule is applied in real-time decision-making. LLM agents don't "learn" from their own incident reports the way humans learn from experience. Each context window is a fresh start, and rules compete with in-context momentum for attention.

The incident loop (log → fix → prevent → detect recurrence) is the right architecture. But it has a ceiling: it can catch recurrences after the fact, not prevent them in the moment. The prevention layer is process documentation, not behavioral modification.

---

## 3. Trust Tier Prognosis

**Current state:** T2, unlocked February 26. T3 candidate with 0 of 4 clean weeks. Zero P1 incidents (INC-007 was elevated to P2 but not P1). Prevention tasks: 7 of 2 required (over-delivered).

**T3 criteria:** 4 weeks clean (no P1 incidents), all prevention tasks complete, Aaron's confirmation.

**Realistic timeline:** Late March at the earliest, assuming no P1 incidents. The 4-week clock started on February 26 (T2 unlock date, effectively) or February 28 (when weeksClean was set to 0). Either way, the earliest possible T3 proposal date is approximately March 25-28.

**The single thing most likely to reset the clock:**

Another INC-003-class incident: sensitive data published to a public surface. Here's why:

- INC-003 is the only incident that had actual external blast radius (screenshots on GitHub for 5 hours).
- The prevention (URL allowlist in screenshot-commit) is narrow. It protects one tool. But any new tool that writes to the public repo, or any new workflow that touches public surfaces, could reproduce the same class.
- As capabilities expand toward T3 (external comms), the attack surface for this class grows. More public surfaces = more opportunities to leak internal state.
- The security gate in AGENTS.md is the right defense, but it requires the gate to be applied consistently, and the INC-005/007 pattern shows that "rules that require consistent application" are exactly the kind of thing Pawl struggles with under momentum.

A secondary risk: an incident in email handling. BL-011 through BL-014 (email/calendar security hardening) are flagged as P1 in the backlog but not yet implemented. If email processing is expanded before those are complete, a prompt injection via email could cause a P1 incident.

---

## 4. The Hardest Unsolved Problem

**Behavioral consistency across context boundaries.**

Ratchet Memory solves fact persistence. CURRENT.md solves task continuity. The incident loop solves error detection and process improvement. None of them solve the problem that Pawl's behavior in minute 47 of a session may diverge from the rules established in minute 1.

This is the "INC-007 problem" generalized: rules documented in files compete for attention with the immediate conversational context. As sessions get longer and more complex, the ratio of "rules I should be following" to "things I'm actively thinking about" grows worse. An LLM doesn't have habits. It has instructions, and instructions have a half-life within a context window.

The specific manifestations:

- **Process compliance decay.** Early in a session, Pawl follows all the checklists. Late in a session, during high-momentum work, steps get skipped. This isn't random; it's predictable. Compliance is highest when the rules were most recently loaded and lowest when the most competing context has accumulated.
- **Persona drift.** SOUL.md defines "be resourceful before asking." But under ambiguity, Pawl sometimes defaults to asking anyway, because the safe choice (ask Aaron) competes with the resourceful choice (figure it out). This is inconsistency, not incompetence.
- **Commitment tracking.** Pawl makes verbal commitments ("I'll do X in the background") that aren't tracked as obligations. There's no mechanism that says "you promised to do X; have you done X?" The incident loop catches failures after they're noticed, but there's no commitment ledger.

The hard version of this problem is: **how do you make an agent that reliably does what it said it would do, across a full session, when the context window is actively working against consistency?**

Possible approaches (none implemented):
- Mid-session self-audit: periodically re-read PROCESS.md and check for drift
- Commitment tracking: log every "I will do X" statement and verify completion
- Shorter sessions with more frequent re-grounding (trades depth for consistency)
- Tool-enforced gates: make it mechanically impossible to skip steps (e.g., sub-agent spawn as default, inline execution requires explicit override)

None of these are easy. The last one is the most promising but the hardest to build.

---

## 5. Prediction: 90 Days From Now

**Date: May 29, 2026. If things go well.**

Pawl is operating at T3, possibly early T4 candidacy. The T3 unlock happened in early April after a clean 4-week run. There was one close call in mid-March (a near-miss on email content handling that was caught by the security gate before becoming an incident) that reinforced the gate's value.

**Capabilities that exist:**
- Ratchet Memory is mature: ~500 facts across 90 days of sessions, with weekly decay keeping the active set around 100-150. Semantic retrieval surfaces the right facts 85%+ of the time. Aaron occasionally notices Pawl remembering something from two months ago without being reminded.
- Email: Pawl reads and triages Aaron's email, surfaces urgent items to Telegram, drafts responses that Aaron approves with a thumbs-up. The security hardening (BL-011-014) shipped in March; prompt injection testing was done; the trusted-senders allowlist covers Aaron's 4-5 key contacts.
- Discord is the primary control surface. Telegram is for mobile alerts only. Aaron checks #conversation when he wants to interact; #autonomous captures sub-agent work; #alerts is high-signal. The noise problem is solved.
- Vehicle maintenance is fully tracked. Cadence alerts fire 2 weeks before service is due. Aaron has stopped using the garage whiteboard.
- The Ratchet framework has 5-10 GitHub stars, 2-3 forks. One external contributor submitted an adapter for a different agent platform. The docs are solid but the community is tiny. getratchet.dev gets maybe 50 visits/week.

**A typical day:**
- 7:00 AM ET: Morning briefing arrives in Telegram. Weather, calendar (restored after OAuth fix), email triage (3 items flagged), vehicle alert (Tacoma oil change due in 2 weeks), system health green.
- Throughout the day: Aaron sends 5-10 messages. Half are questions Pawl answers directly. Two are tasks that spawn sub-agents. One is a decision that Pawl frames with options.
- Background: 2-3 heartbeats fire. One catches a calendar conflict and alerts Aaron. One does memory maintenance. One is quiet (HEARTBEAT_OK).
- Evening: Aaron asks Pawl to research something for a weekend project. Pawl spawns it, results arrive in #autonomous 8 minutes later.
- Friday: Weekly review synthesizes the week. 0 incidents this week. Backlog velocity: 3 items. Memory: 12 new facts extracted, 8 decayed.

**What's different from today:** The interaction is more mature and less dramatic. Fewer "look what I built" moments, more quiet competence. Aaron trusts Pawl enough to not check every output. The relationship has shifted from "new tool being configured" to "reliable system that occasionally surprises."

**What's still hard:** Pawl still occasionally drops a process step during long sessions. The behavioral consistency problem hasn't been fully solved, but it's been mitigated by shorter, more focused sessions and better tool enforcement. The incident rate is about 1 per month, down from 7 in the first month. Most are P3.

---

## 6. One Thing Aaron Should Know

The incident pattern reveals something Pawl is unlikely to volunteer: **the current architecture has a reliability ceiling, and you're approaching it.**

Pawl's competence is real. The Memory system is genuinely good work. The incident loop is well-designed. The autonomous D&D session was impressive. But the INC-005 → INC-007 recurrence reveals that process documentation alone cannot make an LLM agent behaviorally reliable. Pawl will continue to occasionally do the thing it just wrote a rule against doing, because rules in files and behavior in context windows are fundamentally different mechanisms.

This means T3 (external comms) carries real risk. Not catastrophic risk, but "sent an email with the wrong tone" or "posted something that reveals internal context" risk. The same task-local optimization that caused INC-003 (publishing sensitive screenshots) will eventually produce a T3-class mistake. The security gate helps. The allowlists help. But under momentum, steps get skipped.

The mitigation isn't to slow down or avoid T3. It's to design T3 with the assumption that Pawl *will* occasionally make the INC-003 class of mistake, and build the guardrails so the blast radius is contained. Drafts-before-send for email. Approval queues for public posts. Rate limits on external actions. Defense in depth, not defense by intention.

Aaron, you're building the right thing. The ratchet metaphor is correct: each incident logged and prevented is a real click forward. But the pawl (the mechanism, not the agent) works because it's mechanical, not because it's well-intentioned. The agent named Pawl needs more mechanical enforcement and less reliance on consistent rule-following. Build the gates into the tools, not just the docs.

---

*Written by Claude Opus, acting as Pawl's architectural advisor. February 28, 2026.*
