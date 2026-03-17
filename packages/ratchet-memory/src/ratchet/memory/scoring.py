"""Fact scoring — decay, recency, and effective score computation.

Used at retrieval time to rank facts by relevance. Scores are
computed on the fly and never written back to storage.
"""

import math
from datetime import datetime
from typing import Any

DECAY_STANDARD = 0.95
DECAY_TRANSIENT = 0.80


def days_since(date_str: str, today_str: str) -> int:
    try:
        d1 = datetime.strptime(date_str, "%Y-%m-%d")
        d2 = datetime.strptime(today_str, "%Y-%m-%d")
        return max(0, (d2 - d1).days)
    except (ValueError, TypeError):
        return 30


def effective_score(fact: dict[str, Any], today: str) -> float:
    """Score = stored_importance x decay_factor (tier-dependent)."""
    base = float(fact.get("importance", 0.5))
    last_ref = fact.get("last_referenced") or fact.get("created") or today
    weeks = days_since(last_ref, today) / 7.0
    tier = fact.get("tier", "standard")

    if tier == "permanent":
        return base
    if fact.get("superseded_by"):
        return 0.01
    if tier == "transient":
        return base * (DECAY_TRANSIENT ** weeks)
    return base * (DECAY_STANDARD ** weeks)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    denom = norm_a * norm_b
    return dot / denom if denom > 0 else 0.0
