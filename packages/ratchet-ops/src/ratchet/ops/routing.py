"""Cost-aware model routing — route tasks to the cheapest model that handles them well.

Maps task complexity to models: Haiku for simple tasks, Sonnet for medium,
Opus for complex. Tracks cumulative cost and provides cost projections.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("ratchet.ops.routing")

# Pricing per million tokens (as of 2026)
DEFAULT_PRICING = {
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}

# Task complexity → model mapping
COMPLEXITY_MAP = {
    "simple": "claude-haiku-4-5",      # Fact extraction, classification, formatting
    "medium": "claude-sonnet-4-20250514",  # Synthesis, code review, analysis
    "complex": "claude-opus-4-20250514",   # Architecture, deep reasoning, novel problems
}

# Keywords that suggest complexity level
SIMPLE_SIGNALS = [
    "extract", "classify", "format", "parse", "list", "count",
    "summarize briefly", "yes or no", "true or false",
]
COMPLEX_SIGNALS = [
    "architecture", "design", "critique", "novel", "creative",
    "strategy", "evaluate tradeoffs", "deep analysis", "review code",
]


@dataclass
class CostEntry:
    """A logged API cost entry."""
    model: str = ""
    call_type: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: str = ""


@dataclass
class CostSummary:
    """Cost summary for a period."""
    period: str = ""
    total_cost: float = 0.0
    by_model: dict[str, float] = field(default_factory=dict)
    by_call_type: dict[str, float] = field(default_factory=dict)
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0


def estimate_complexity(task_description: str) -> str:
    """
    Estimate task complexity from description.

    Returns: "simple", "medium", or "complex"
    """
    desc_lower = task_description.lower()

    if any(signal in desc_lower for signal in COMPLEX_SIGNALS):
        return "complex"
    if any(signal in desc_lower for signal in SIMPLE_SIGNALS):
        return "simple"

    # Default to medium for ambiguous tasks
    return "medium"


def select_model(
    task_description: str,
    complexity: str | None = None,
    custom_map: dict[str, str] | None = None,
) -> str:
    """
    Select the best model for a task based on complexity.

    Args:
        task_description: Description of the task.
        complexity: Override complexity ("simple", "medium", "complex").
        custom_map: Override the complexity→model mapping.

    Returns:
        Model identifier string.
    """
    if complexity is None:
        complexity = estimate_complexity(task_description)

    model_map = custom_map or COMPLEXITY_MAP
    model = model_map.get(complexity, COMPLEXITY_MAP["medium"])

    logger.debug(f"Routed '{task_description[:40]}' → {complexity} → {model}")
    return model


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    pricing: dict[str, dict[str, float]] | None = None,
) -> float:
    """Calculate cost in USD for a model call."""
    pricing = pricing or DEFAULT_PRICING
    if model not in pricing:
        logger.warning(f"Unknown model for pricing: {model}")
        return 0.0

    rates = pricing[model]
    cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
    return round(cost, 6)


def log_cost(
    model: str,
    call_type: str,
    input_tokens: int,
    output_tokens: int,
    store_dir: Path | str,
    pricing: dict[str, dict[str, float]] | None = None,
) -> CostEntry:
    """Log an API call cost to the cost log."""
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    cost_file = store_dir / "cost-log.jsonl"

    cost = calculate_cost(model, input_tokens, output_tokens, pricing)
    now = datetime.now(timezone.utc).isoformat()

    entry = CostEntry(
        model=model, call_type=call_type,
        input_tokens=input_tokens, output_tokens=output_tokens,
        cost_usd=cost, timestamp=now,
    )

    data = {
        "model": model, "call_type": call_type,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "cost_usd": cost, "timestamp": now,
    }

    with open(cost_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")

    return entry


def summarize_costs(
    store_dir: Path | str,
    period: str = "month",
) -> CostSummary:
    """Summarize API costs for a period."""
    store_dir = Path(store_dir)
    cost_file = store_dir / "cost-log.jsonl"

    if not cost_file.exists():
        return CostSummary(period=period)

    now = datetime.now(timezone.utc)
    if period == "day":
        since = (now - timedelta(days=1)).isoformat()
    elif period == "week":
        since = (now - timedelta(days=7)).isoformat()
    elif period == "month":
        since = (now - timedelta(days=30)).isoformat()
    else:
        since = ""

    summary = CostSummary(period=period)

    with open(cost_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if since and data.get("timestamp", "") < since:
                    continue
                cost = data.get("cost_usd", 0)
                model = data.get("model", "unknown")
                call_type = data.get("call_type", "unknown")

                summary.total_cost += cost
                summary.by_model[model] = summary.by_model.get(model, 0) + cost
                summary.by_call_type[call_type] = summary.by_call_type.get(call_type, 0) + cost
                summary.total_calls += 1
                summary.total_input_tokens += data.get("input_tokens", 0)
                summary.total_output_tokens += data.get("output_tokens", 0)
            except json.JSONDecodeError:
                pass

    summary.total_cost = round(summary.total_cost, 4)
    summary.by_model = {k: round(v, 4) for k, v in sorted(summary.by_model.items(), key=lambda x: -x[1])}
    summary.by_call_type = {k: round(v, 4) for k, v in sorted(summary.by_call_type.items(), key=lambda x: -x[1])}

    return summary
