"""Guardrail matching and preflight checks."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("ratchet.pilot.guardrails")


@dataclass
class GuardrailMatch:
    id: str
    source: str
    pattern: str
    rule: str
    severity: str
    trigger: str
    matched_keywords: list[str] = field(default_factory=list)


@dataclass
class PreflightResult:
    action: str = ""
    overall_severity: str = "clear"
    matches: list[GuardrailMatch] = field(default_factory=list)
    verdict: str = ""

    @property
    def is_clear(self) -> bool:
        return self.overall_severity == "clear"

    @property
    def is_hard(self) -> bool:
        return self.overall_severity == "hard"


def load_guardrails(guardrails_path: Path | str) -> list[dict[str, Any]]:
    path = Path(guardrails_path)
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def match_guardrails(action_text: str, guardrails: list[dict[str, Any]]) -> list[GuardrailMatch]:
    action_lower = action_text.lower()
    matches = []
    for gr in guardrails:
        matched = [kw for kw in gr.get("keywords", []) if kw.lower() in action_lower]
        if matched:
            matches.append(GuardrailMatch(
                id=gr.get("id", ""), source=gr.get("source", ""), pattern=gr.get("pattern", ""),
                rule=gr.get("rule", ""), severity=gr.get("severity", "soft"),
                trigger=gr.get("trigger", ""), matched_keywords=matched))
    return matches


def update_fire_counts(guardrail_ids: list[str], guardrails_path: Path | str) -> None:
    path = Path(guardrails_path)
    if not path.exists():
        return
    with open(path) as f:
        guardrails = json.load(f)
    now = datetime.now(timezone.utc).isoformat()
    updated = False
    for gr in guardrails:
        if gr.get("id") in guardrail_ids:
            gr["fire_count"] = gr.get("fire_count", 0) + 1
            gr["last_fired"] = now
            updated = True
    if updated:
        with open(path, "w") as f:
            json.dump(guardrails, f, indent=2)


def preflight_check(action_text: str, guardrails_path: Path | str, update_counts: bool = False) -> PreflightResult:
    guardrails = load_guardrails(guardrails_path)
    matches = match_guardrails(action_text, guardrails)
    overall = "clear"
    if matches:
        overall = "hard" if any(m.severity == "hard" for m in matches) else "soft"
    verdicts = {"clear": "CLEAR — no guardrails matched. Proceed.",
                "soft": "SOFT MATCH — review rules before proceeding.",
                "hard": "HARD MATCH — pause and verify. Consider pause-and-ask."}
    result = PreflightResult(action=action_text, overall_severity=overall, matches=matches, verdict=verdicts[overall])
    if update_counts and matches:
        update_fire_counts([m.id for m in matches], guardrails_path)
    return result
