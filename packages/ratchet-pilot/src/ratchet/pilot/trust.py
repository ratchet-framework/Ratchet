"""Trust tier evaluation — evidence-based autonomy expansion."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ratchet.pilot.incidents import Incident, count_by_severity, filter_recent

logger = logging.getLogger("ratchet.pilot.trust")


@dataclass
class TrustTrigger:
    name: str
    triggered: bool = False
    rule: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Regression:
    required: bool = False
    action: str | None = None
    reason: str | None = None
    tiers: int = 0
    weeks: int = 0
    recovery: str | None = None
    new_tier: int | None = None


@dataclass
class TrustCheckResult:
    checked_at: str = ""
    current_tier: int = 0
    triggers: dict[str, TrustTrigger] = field(default_factory=dict)
    regression: Regression = field(default_factory=Regression)
    incident_counts: dict[str, int] = field(default_factory=dict)


def load_trust(trust_path: Path | str) -> dict[str, Any]:
    path = Path(trust_path)
    if not path.exists():
        raise FileNotFoundError(f"trust.json not found: {path}")
    return json.loads(path.read_text())


def evaluate_triggers(incidents: list[Incident], trust: dict[str, Any]) -> dict[str, TrustTrigger]:
    rr = trust.get("regressionRules", {})
    recent = filter_recent(incidents, weeks=4)
    recent_p1 = [i for i in recent if i.severity == "P1"]
    recent_p2 = [i for i in recent if i.severity == "P2"]
    triggers: dict[str, TrustTrigger] = {}

    p1_ext = [i for i in recent_p1 if i.external_impact]
    triggers["p1ExternalImpact"] = TrustTrigger(name="p1ExternalImpact", triggered=len(p1_ext) > 0,
        rule=rr.get("p1ExternalImpact", {}), evidence=[i.file for i in p1_ext])

    p1_no_ext = [i for i in recent_p1 if not i.external_impact]
    triggers["p1NoExternalImpact"] = TrustTrigger(name="p1NoExternalImpact", triggered=len(p1_no_ext) > 0,
        rule=rr.get("p1NoExternalImpact", {}), evidence=[i.file for i in p1_no_ext])

    p2_by_class: dict[str, list[str]] = {}
    for i in recent_p2:
        p2_by_class.setdefault(i.incident_class, []).append(i.file)
    repeat = {c: f for c, f in p2_by_class.items() if len(f) >= 2}
    triggers["p2SameClass2in4weeks"] = TrustTrigger(name="p2SameClass2in4weeks", triggered=len(repeat) > 0,
        rule=rr.get("p2SameClass2in4weeks", {}), extra={"classes": repeat})

    triggers["p2Any3in4weeks"] = TrustTrigger(name="p2Any3in4weeks", triggered=len(recent_p2) >= 3,
        rule=rr.get("p2Any3in4weeks", {}), extra={"count": len(recent_p2)})

    systemic = [i for i in recent if i.systemic_flag]
    triggers["patternSystemic"] = TrustTrigger(name="patternSystemic", triggered=len(systemic) > 0,
        rule=rr.get("patternSystemic", {}), evidence=[i.file for i in systemic])

    return triggers


def determine_regression(triggers: dict[str, TrustTrigger], current_tier: int) -> Regression:
    for name in ("p1ExternalImpact", "p2Any3in4weeks"):
        t = triggers.get(name)
        if t and t.triggered:
            rule = t.rule
            return Regression(required=True, action=rule.get("action", "drop"), reason=name,
                tiers=rule.get("tiers", 1), recovery=rule.get("recovery", "full-requalification"),
                new_tier=max(1, current_tier - rule.get("tiers", 1)))

    for name in ("p1NoExternalImpact", "p2SameClass2in4weeks"):
        t = triggers.get(name)
        if t and t.triggered:
            rule = t.rule
            return Regression(required=True, action=rule.get("action", "freeze"), reason=name,
                weeks=rule.get("weeks", 2), recovery=rule.get("recovery", "prevention-plus-clean"))

    t = triggers.get("patternSystemic")
    if t and t.triggered:
        return Regression(required=True, action=t.rule.get("action", "aaron-review"),
            reason="patternSystemic", recovery=t.rule.get("recovery", "aaron-decides"))

    return Regression()


def apply_regression(regression: Regression, trust: dict[str, Any], trust_path: Path | str) -> dict[str, Any]:
    if not regression.required:
        return trust
    current = trust.get("currentTier", 2)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if regression.action == "drop":
        new_tier = regression.new_tier or max(1, current - 1)
        trust["currentTier"] = new_tier
        trust.setdefault("regressionHistory", []).append({"from": current, "to": new_tier, "date": today, "reason": regression.reason})
    elif regression.action == "freeze":
        trust["advancementFrozen"] = True
        trust["advancementFreezeUntil"] = (datetime.now(timezone.utc) + timedelta(weeks=regression.weeks)).strftime("%Y-%m-%d")
        trust.setdefault("regressionHistory", []).append({"from": current, "to": current, "date": today, "action": "freeze", "reason": regression.reason})
    elif regression.action == "aaron-review":
        trust["requiresAaronReview"] = True
        trust.setdefault("regressionHistory", []).append({"from": current, "to": current, "date": today, "action": "aaron-review", "reason": regression.reason})

    trust["updatedAt"] = today
    Path(trust_path).write_text(json.dumps(trust, indent=2) + "\n")
    return trust


def check_trust(incidents: list[Incident], trust_path: Path | str, apply: bool = False) -> TrustCheckResult:
    trust = load_trust(trust_path)
    current_tier = trust.get("currentTier", 2)
    four_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=4)

    triggers = evaluate_triggers(incidents, trust)
    regression = determine_regression(triggers, current_tier)

    if apply and regression.required:
        apply_regression(regression, trust, trust_path)

    all_counts = count_by_severity(incidents)
    recent_counts = count_by_severity(incidents, since=four_weeks_ago)

    return TrustCheckResult(
        checked_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        current_tier=current_tier, triggers=triggers, regression=regression,
        incident_counts={
            "p1_last_4_weeks": recent_counts["P1"], "p2_last_4_weeks": recent_counts["P2"],
            "p3_last_4_weeks": recent_counts["P3"],
            "p1_total": all_counts["P1"], "p2_total": all_counts["P2"], "p3_total": all_counts["P3"],
        })
