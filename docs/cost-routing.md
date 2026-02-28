# Cost-Aware Model Routing

One of Ratchet's core primitives. Every task gets routed to the cheapest model that can handle it well.

## Why it matters

Routing every task to your most capable (expensive) model is the default. It's also wasteful. A heartbeat check doesn't need the same model as a strategic planning session. Over time, unoptimized routing is the single largest avoidable cost for agents running continuously.

Cost-aware routing is also self-compounding: savings fund more capability, which means more integrations, more automation, more value — all at lower marginal cost over time.

## Three tiers

| Tier | Purpose | Cost profile |
|------|---------|-------------|
| **1 — Simple** | Routine checks, notifications, lookups | ~$0.001/run |
| **2 — Synthesis** | Writing, analysis, conversation, judgment calls | ~$0.020/run |
| **3 — Deep** | Architecture, high-stakes decisions, complex reasoning | ~$0.100/run |

## Decision flow

```
Is this a routine check or notification?  →  Tier 1
Does this require judgment or synthesis?  →  Tier 2
Deep reasoning or high-stakes decision?  →  Tier 3
Default                                   →  Tier 2
```

## Adapter mapping

Each Ratchet adapter defines its own model-to-tier mapping:

```json
{
  "tier1": "fast-cheap-model",
  "tier2": "capable-mid-model",
  "tier3": "most-capable-model"
}
```

**OpenClaw reference implementation:**
```json
{
  "tier1": "anthropic/claude-haiku-4-5",
  "tier2": "anthropic/claude-sonnet-4-6",
  "tier3": "anthropic/claude-opus-4-6"
}
```

## Cost tracking

Log every automated task with the `cost-log` tool:

```bash
cost-log --tier 1 --task heartbeat --model haiku
cost-log --summary
```

Output:
```
Cost summary (week of 2026-02-23):
  Runs this week : 48
  Estimated cost : $0.14
  Naive cost     : $0.96  (all at Sonnet)
  Saved          : $0.82
```

## Real numbers

A heartbeat running every 30 minutes:
- At Sonnet: ~$0.96/day, ~$29/month
- At Haiku: ~$0.048/day, ~$1.44/month
- **Savings: ~$27.56/month — just on heartbeats**

That savings compounds as you add more automated tasks.

## Capability unlock

Add `cost-routing` to your `capabilities.json` once you've implemented tier-based routing with cost logging.
