#!/bin/bash
# Run from C:/Projects/Ratchet on the modularize branch
# Adds the complete ratchet-pilot package
set -e

echo "🧭 Adding ratchet-pilot package..."

# Create namespace init
mkdir -p packages/ratchet-pilot/src/ratchet/pilot
echo '__path__ = __import__("pkgutil").extend_path(__path__, __name__)' > packages/ratchet-pilot/src/ratchet/__init__.py

# --- pyproject.toml ---
cat > packages/ratchet-pilot/pyproject.toml << 'EOF'
[project]
name = "ratchet-pilot"
version = "0.1.0"
description = "Self-improvement engine for the Ratchet framework"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Aaron Benson" },
]
dependencies = [
    "ratchet-core>=0.1.0",
]

[project.urls]
Homepage = "https://getratchet.dev"
Repository = "https://github.com/ratchet-framework/Ratchet"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ratchet"]

[tool.hatch.build.targets.editable]
packages = ["src/ratchet"]
EOF

# --- README.md ---
cat > packages/ratchet-pilot/README.md << 'EOF'
# ratchet-pilot

Self-improvement engine for the [Ratchet framework](https://getratchet.dev).

- **Incidents** — Parse INC-*.md postmortems with severity, prevention tasks, root cause
- **Trust** — Evidence-based autonomy tiers (T1-T5) with automatic regression
- **Guardrails** — Preflight checks against keyword-matched rules
- **Actions** — Pause-and-ask queue with severity-based timeouts
- **Metrics** — Weekly incident health, backlog velocity, adoption stats

## Install

```bash
pip install ratchet-pilot
```

## License

MIT
EOF

# --- incidents.py ---
cat > packages/ratchet-pilot/src/ratchet/pilot/incidents.py << 'PYEOF'
"""Incident file parsing — shared by trust, metrics, and reporting."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass
class Incident:
    file: str = ""
    date: str | None = None
    datetime_utc: datetime | None = None
    status: str = "UNKNOWN"
    severity: str = "UNKNOWN"
    external_impact: bool = False
    incident_class: str = "unknown"
    systemic_flag: bool = False
    root_cause_summary: str = ""
    prevention_total: int = 0
    prevention_done: int = 0

    @property
    def is_open(self) -> bool:
        return self.status.upper() in ("OPEN", "IN PROGRESS")

    @property
    def is_resolved(self) -> bool:
        return "RESOLVED" in self.status.upper()

    @property
    def prevention_complete(self) -> bool:
        return self.prevention_total > 0 and self.prevention_done == self.prevention_total


_SEVERITY_MAP = {
    "P1": "P1", "CRITICAL": "P1", "SEV1": "P1", "SEV-1": "P1",
    "P2": "P2", "HIGH": "P2", "SEV2": "P2", "SEV-2": "P2",
    "P3": "P3", "MEDIUM": "P3", "SEV3": "P3", "SEV-3": "P3", "LOW": "P3",
}


def parse_incident_file(path: Path) -> Incident:
    text = path.read_text(errors="replace")
    inc = Incident(file=path.name)

    m = re.search(r"^Date:\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
    if m:
        inc.date = m.group(1)
        try:
            inc.datetime_utc = datetime.fromisoformat(inc.date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    m = re.search(r"^Status:\s*(.+)", text, re.MULTILINE)
    if m:
        inc.status = m.group(1).strip()

    m = re.search(r"^Severity:\s*(.+)", text, re.MULTILINE)
    if m:
        raw = m.group(1).strip().upper()
        inc.severity = _SEVERITY_MAP.get(raw, "UNKNOWN")

    inc.external_impact = bool(re.search(
        r"(external\s+impact|leaked\s+(externally|publicly)|public\s+exposure|wrong\s+recipient|sent\s+to\s+wrong)",
        text, re.IGNORECASE))

    m = re.match(r"INC-\d+-(.+)\.md", path.name)
    if m:
        inc.incident_class = re.sub(r"[-_](repeated|again|redux|\d+)$", "", m.group(1))

    inc.systemic_flag = bool(re.search(
        r"(systemic|pattern\s+failure|recurring\s+class|same\s+class)", text, re.IGNORECASE))

    m = re.search(r"## Root cause\s*\n+(.+)", text)
    if m:
        inc.root_cause_summary = m.group(1).strip()[:80]

    tasks = re.findall(r"- \[(x| )\]", text, re.IGNORECASE)
    inc.prevention_total = len(tasks)
    inc.prevention_done = sum(1 for t in tasks if t.lower() == "x")

    return inc


def parse_all_incidents(incidents_dir: Path | str) -> list[Incident]:
    incidents_dir = Path(incidents_dir)
    if not incidents_dir.exists():
        return []
    return [parse_incident_file(p) for p in sorted(incidents_dir.glob("INC-*.md")) if p.name != "README.md"]


def filter_recent(incidents: list[Incident], weeks: int = 4) -> list[Incident]:
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    return [i for i in incidents if i.datetime_utc and i.datetime_utc >= cutoff]


def count_by_severity(incidents: list[Incident], since: datetime | None = None) -> dict[str, int]:
    counts = {"P1": 0, "P2": 0, "P3": 0, "UNKNOWN": 0}
    for inc in incidents:
        if since and (not inc.datetime_utc or inc.datetime_utc < since):
            continue
        counts[inc.severity if inc.severity in counts else "UNKNOWN"] += 1
    return counts


def recurring_classes(incidents: list[Incident]) -> dict[str, int]:
    cc: dict[str, int] = {}
    for inc in incidents:
        cc[inc.incident_class] = cc.get(inc.incident_class, 0) + 1
    return {c: n for c, n in cc.items() if n > 1}
PYEOF

# --- trust.py ---
cat > packages/ratchet-pilot/src/ratchet/pilot/trust.py << 'PYEOF'
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
PYEOF

# --- guardrails.py ---
cat > packages/ratchet-pilot/src/ratchet/pilot/guardrails.py << 'PYEOF'
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
PYEOF

# --- actions.py ---
cat > packages/ratchet-pilot/src/ratchet/pilot/actions.py << 'PYEOF'
"""Pending action queue — pause-and-ask + approve/deny."""

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("ratchet.pilot.actions")

TIMEOUTS = {"destructive": None, "time-sensitive": 14400, "informational": 1800}
ACTION_ID_RE = re.compile(r"^[0-9a-f]{8}$")


@dataclass
class PendingAction:
    id: str
    action: str
    trigger: str
    context: str
    severity: str
    requested_at: str
    status: str = "pending"
    timeout_seconds: int | None = None
    resolved_at: str | None = None
    resolved_by: str | None = None


def _load_pending(p: Path) -> list[dict[str, Any]]:
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def _save_pending(pending: list, p: Path) -> None:
    tmp = str(p) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(pending, f, indent=2)
    os.replace(tmp, str(p))


def _append_audit(entry: dict, status: str, actor: str, audit: Path) -> None:
    audit.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with open(audit, "a") as f:
        f.write(f"{now} | id={entry['id']} | action={entry['action']!r} | severity={entry['severity']} | status={status} | actor={actor}\n")


def check_timeouts(pending: list[dict]) -> tuple[list[dict], bool]:
    now = datetime.now(timezone.utc)
    changed = False
    for e in pending:
        if e["status"] != "pending":
            continue
        t = e.get("timeout_seconds")
        if t is None:
            continue
        if (now - datetime.fromisoformat(e["requested_at"])).total_seconds() > t:
            e["status"] = "expired"
            e["resolved_at"] = now.isoformat()
            e["resolved_by"] = "timeout"
            changed = True
    return pending, changed


def queue_action(action: str, trigger: str, context: str, severity: str, workspace: Path | str) -> PendingAction:
    ws = Path(workspace)
    pp = ws / "pending-actions.json"
    aid = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    entry = {"id": aid, "action": action, "trigger": trigger, "context": context, "severity": severity,
             "requested_at": now, "status": "pending", "timeout_seconds": TIMEOUTS.get(severity),
             "resolved_at": None, "resolved_by": None}
    pending = _load_pending(pp)
    pending.append(entry)
    _save_pending(pending, pp)
    return PendingAction(id=aid, action=action, trigger=trigger, context=context,
                        severity=severity, requested_at=now, timeout_seconds=TIMEOUTS.get(severity))


def review_action(action_id: str, decision: str, workspace: Path | str, actor: str = "aaron") -> dict | None:
    ws = Path(workspace)
    pp = ws / "pending-actions.json"
    audit = ws / "memory" / "comms-review-audit.log"
    pending = _load_pending(pp)
    pending, _ = check_timeouts(pending)
    entry = next((p for p in pending if p["id"] == action_id), None)
    if not entry:
        return None
    if entry["status"] != "pending":
        return entry
    now = datetime.now(timezone.utc).isoformat()
    entry["status"] = "approved" if decision == "approve" else "denied"
    entry["resolved_at"] = now
    entry["resolved_by"] = actor
    _save_pending(pending, pp)
    _append_audit(entry, entry["status"], actor, audit)
    return entry


def list_pending(workspace: Path | str, include_resolved: bool = False) -> list[dict]:
    ws = Path(workspace)
    pp = ws / "pending-actions.json"
    pending = _load_pending(pp)
    pending, changed = check_timeouts(pending)
    if changed:
        _save_pending(pending, pp)
    return pending if include_resolved else [p for p in pending if p["status"] == "pending"]
PYEOF

# --- metrics.py ---
cat > packages/ratchet-pilot/src/ratchet/pilot/metrics.py << 'PYEOF'
"""Weekly metrics collection."""

import json
import logging
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ratchet.pilot.incidents import Incident, count_by_severity, recurring_classes

logger = logging.getLogger("ratchet.pilot.metrics")


@dataclass
class WeeklyMetrics:
    week: str = ""
    incidents: dict[str, Any] = field(default_factory=dict)
    backlog: dict[str, Any] = field(default_factory=dict)
    adoption: dict[str, Any] = field(default_factory=dict)
    weeks_since_last_incident: float | None = None
    incident_severity_distribution: dict[str, int] = field(default_factory=dict)
    trust_tier_readiness: bool = False


def _today():
    return datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d")

def _week_ago():
    return datetime.now(timezone.utc) - timedelta(days=7)


def collect_incident_metrics(incidents: list[Incident]) -> dict[str, Any]:
    cutoff = _week_ago()
    opened = sum(1 for i in incidents if i.datetime_utc and i.datetime_utc >= cutoff)
    closed = sum(1 for i in incidents if i.is_resolved and i.datetime_utc and i.datetime_utc >= cutoff)
    return {
        "opened_this_week": opened, "closed_this_week": closed,
        "total_open": sum(1 for i in incidents if i.is_open),
        "total_all_time": len(incidents),
        "recurring_classes": recurring_classes(incidents),
    }


def collect_backlog_metrics(backlog_path: Path | str) -> dict[str, Any]:
    path = Path(backlog_path)
    if not path.exists():
        return {"active": 0, "completed_all_time": 0, "velocity_this_week": 0}
    text = path.read_text(errors="replace")
    rows = re.findall(r"^\|.*BL-\d+.*\|", text, re.MULTILINE)
    active = sum(1 for r in rows if "~~" not in r)
    completed = sum(1 for r in rows if "~~" in r)
    velocity = 0
    cutoff = _week_ago()
    for d in re.findall(r"\|[^|]*~~[^|]*~~[^|]*\|\s*(\d{4}-\d{2}-\d{2})\s*\|", text):
        try:
            if datetime.fromisoformat(d).replace(tzinfo=timezone.utc) >= cutoff:
                velocity += 1
        except ValueError:
            pass
    return {"active": active, "completed_all_time": completed, "velocity_this_week": velocity}


def collect_adoption_metrics(github_repo: str = "ratchet-framework/Ratchet") -> dict[str, Any]:
    result: dict[str, Any] = {"stars": None, "forks": None, "open_issues": None}
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{github_repo}",
                                    headers={"User-Agent": "ratchet-metrics/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        result["stars"] = int(data.get("stargazers_count", 0))
        result["forks"] = int(data.get("forks_count", 0))
        result["open_issues"] = int(data.get("open_issues_count", 0))
    except Exception as e:
        logger.warning(f"GitHub API error: {e}")
    return result


def weeks_since_last_incident(incidents: list[Incident]) -> float | None:
    dated = [i for i in incidents if i.datetime_utc]
    if not dated:
        return None
    latest = max(dated, key=lambda i: i.datetime_utc)
    return round((datetime.now(timezone.utc) - latest.datetime_utc).days / 7, 1)


def severity_distribution(incidents: list[Incident], weeks: int = 4) -> dict[str, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    recent = [i for i in incidents if i.datetime_utc and i.datetime_utc >= cutoff]
    dist = {"P1": 0, "P2": 0, "P3": 0}
    for i in recent:
        if i.severity in dist:
            dist[i.severity] += 1
    return dist


def collect_metrics(incidents: list[Incident], backlog_path: Path | str | None = None,
                   github_repo: str | None = None, trust_data: dict | None = None) -> WeeklyMetrics:
    m = WeeklyMetrics(week=_today())
    m.incidents = collect_incident_metrics(incidents)
    if backlog_path:
        m.backlog = collect_backlog_metrics(backlog_path)
    if github_repo:
        m.adoption = collect_adoption_metrics(github_repo)
    m.weeks_since_last_incident = weeks_since_last_incident(incidents)
    m.incident_severity_distribution = severity_distribution(incidents, weeks=4)
    return m


def save_metrics(metrics: WeeklyMetrics, metrics_path: Path | str) -> None:
    path = Path(metrics_path)
    existing = json.loads(path.read_text()) if path.exists() else {"schema": "ratchet-metrics-v1", "entries": []}
    existing["entries"] = [e for e in existing["entries"] if e.get("week") != metrics.week]
    existing["entries"].append({
        "week": metrics.week, "incidents": metrics.incidents, "backlog": metrics.backlog,
        "ratchet": metrics.adoption, "weeks_since_last_incident": metrics.weeks_since_last_incident,
        "incident_severity_distribution": metrics.incident_severity_distribution,
        "trust_tier_readiness": metrics.trust_tier_readiness,
    })
    existing["entries"].sort(key=lambda e: e["week"])
    path.write_text(json.dumps(existing, indent=2) + "\n")
PYEOF

# --- module.py ---
cat > packages/ratchet-pilot/src/ratchet/pilot/module.py << 'PYEOF'
"""PilotModule — Ratchet's self-improvement engine."""

import logging
from pathlib import Path
from typing import Any, Optional

from ratchet.core.module import RatchetModule
from ratchet.pilot.actions import list_pending
from ratchet.pilot.guardrails import PreflightResult, load_guardrails, preflight_check
from ratchet.pilot.incidents import parse_all_incidents, filter_recent
from ratchet.pilot.metrics import WeeklyMetrics, collect_metrics, save_metrics
from ratchet.pilot.trust import TrustCheckResult, check_trust, load_trust

logger = logging.getLogger("ratchet.pilot")


class PilotModule(RatchetModule):
    """Self-improvement engine: incidents, trust, guardrails, metrics, actions."""

    name = "pilot"
    version = "0.1.0"

    def __init__(self) -> None:
        self.agent = None
        self._incidents_dir: Path | None = None
        self._trust_path: Path | None = None
        self._guardrails_path: Path | None = None
        self._backlog_path: Path | None = None
        self._metrics_path: Path | None = None
        self._github_repo: str | None = None
        self._last_trust_check: TrustCheckResult | None = None

    async def initialize(self, agent, config: dict[str, Any]) -> None:
        self.agent = agent
        ws = agent.workspace
        self._incidents_dir = ws / config.get("incidents_dir", "incidents")
        self._trust_path = ws / config.get("trust_path", "config/trust.json")
        self._guardrails_path = ws / config.get("guardrails_path", "config/guardrails.json")
        self._backlog_path = ws / config.get("backlog_path", "BACKLOG.md")
        self._metrics_path = ws / config.get("metrics_path", "metrics.json")
        self._github_repo = config.get("github_repo")
        agent.bus.subscribe("pilot.incident_detected", self._handle_incident_detected)
        logger.info(f"Pilot initialized: incidents={self._incidents_dir}, trust={self._trust_path}")

    async def on_session_start(self, context: dict[str, Any]) -> None:
        status: dict[str, Any] = {}
        incidents = parse_all_incidents(self._incidents_dir)
        open_incs = [i for i in incidents if i.is_open]
        if open_incs:
            status["open_incidents"] = [{"file": i.file, "severity": i.severity,
                "open_tasks": i.prevention_total - i.prevention_done} for i in open_incs]
        guardrails = load_guardrails(self._guardrails_path)
        if guardrails:
            status["guardrails"] = {"total": len(guardrails),
                "hard": sum(1 for g in guardrails if g.get("severity") == "hard"),
                "soft": sum(1 for g in guardrails if g.get("severity") == "soft")}
        pending = list_pending(self.agent.workspace)
        if pending:
            status["pending_actions"] = len(pending)
        if self._trust_path.exists():
            trust = load_trust(self._trust_path)
            status["trust_tier"] = trust.get("currentTier", 0)
            if trust.get("advancementFrozen"):
                status["advancement_frozen"] = True
                status["freeze_until"] = trust.get("advancementFreezeUntil", "?")
        context["pilot_status"] = status

    async def on_session_end(self, context: dict[str, Any]) -> None:
        if not self._trust_path.exists():
            return
        incidents = parse_all_incidents(self._incidents_dir)
        if incidents:
            result = check_trust(incidents, self._trust_path)
            self._last_trust_check = result
            if result.regression.required:
                await self.agent.bus.publish("pilot.regression_detected", {
                    "action": result.regression.action, "reason": result.regression.reason,
                    "current_tier": result.current_tier})

    async def on_heartbeat(self) -> Optional[dict[str, Any]]:
        stats: dict[str, Any] = {"status": "healthy"}
        incidents = parse_all_incidents(self._incidents_dir)
        recent = filter_recent(incidents, weeks=4)
        stats["incidents"] = {"total": len(incidents), "open": sum(1 for i in incidents if i.is_open),
                             "last_4_weeks": len(recent)}
        if self._trust_path.exists():
            trust = load_trust(self._trust_path)
            stats["trust_tier"] = trust.get("currentTier", 0)
            stats["advancement_frozen"] = trust.get("advancementFrozen", False)
        stats["pending_actions"] = len(list_pending(self.agent.workspace))
        stats["guardrails"] = len(load_guardrails(self._guardrails_path))
        return stats

    async def _handle_incident_detected(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._trust_path.exists():
            incidents = parse_all_incidents(self._incidents_dir)
            self._last_trust_check = check_trust(incidents, self._trust_path)

    def run_preflight(self, action_text: str, update_counts: bool = False) -> PreflightResult:
        return preflight_check(action_text, self._guardrails_path, update_counts)

    def run_trust_check(self, apply: bool = False) -> TrustCheckResult:
        incidents = parse_all_incidents(self._incidents_dir)
        result = check_trust(incidents, self._trust_path, apply=apply)
        self._last_trust_check = result
        return result

    def run_metrics_collection(self, save: bool = True) -> WeeklyMetrics:
        incidents = parse_all_incidents(self._incidents_dir)
        trust_data = load_trust(self._trust_path) if self._trust_path.exists() else None
        metrics = collect_metrics(incidents=incidents, backlog_path=self._backlog_path,
                                github_repo=self._github_repo, trust_data=trust_data)
        if save and self._metrics_path:
            save_metrics(metrics, self._metrics_path)
        return metrics
PYEOF

# --- __init__.py ---
cat > packages/ratchet-pilot/src/ratchet/pilot/__init__.py << 'PYEOF'
"""ratchet.pilot — Self-improvement engine: incidents, trust, guardrails, metrics."""

from ratchet.pilot.module import PilotModule
from ratchet.pilot.incidents import Incident, parse_all_incidents, filter_recent, count_by_severity, recurring_classes
from ratchet.pilot.trust import TrustCheckResult, TrustTrigger, Regression, check_trust, evaluate_triggers, load_trust
from ratchet.pilot.guardrails import PreflightResult, GuardrailMatch, preflight_check, load_guardrails
from ratchet.pilot.actions import PendingAction, queue_action, review_action, list_pending
from ratchet.pilot.metrics import WeeklyMetrics, collect_metrics, save_metrics

__all__ = [
    "PilotModule",
    "Incident", "parse_all_incidents", "filter_recent", "count_by_severity", "recurring_classes",
    "TrustCheckResult", "TrustTrigger", "Regression", "check_trust", "evaluate_triggers", "load_trust",
    "PreflightResult", "GuardrailMatch", "preflight_check", "load_guardrails",
    "PendingAction", "queue_action", "review_action", "list_pending",
    "WeeklyMetrics", "collect_metrics", "save_metrics",
]
PYEOF

# --- Update Pawl to register PilotModule ---
cat > agents/pawl/pawl.py << 'PYEOF'
"""Pawl — Ratchet reference agent."""

import asyncio
import logging
from ratchet.core import Agent
from ratchet.memory import MemoryModule
from ratchet.pilot import PilotModule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    agent = Agent(name="Pawl", config_path="agents/pawl/config/context.json")
    agent.register(MemoryModule())
    agent.register(PilotModule())

    await agent.start()
    print(f"\n✅ Agent '{agent.name}' started with {len(agent.modules)} module(s):")
    for mod in agent.modules:
        print(f"   {mod}")

    report = await agent.heartbeat()
    print(f"\n💓 Heartbeat report:")
    for name, status in report.items():
        print(f"   {name}: {status}")

    await agent.stop()
    print(f"\n🔩 Agent stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
PYEOF

# --- Add pilot config to Pawl's context.json ---
python3 -c "
import json
p = 'agents/pawl/config/context.json'
c = json.load(open(p))
c['pilot'] = {
    'incidents_dir': 'incidents',
    'trust_path': 'config/trust.json',
    'guardrails_path': 'config/guardrails.json',
    'backlog_path': 'BACKLOG.md',
    'metrics_path': 'metrics.json',
    'github_repo': 'ratchet-framework/Ratchet'
}
json.dump(c, open(p, 'w'), indent=2)
print('  Updated context.json with pilot config')
"

echo ""
echo "✅ ratchet-pilot added!"
echo ""
echo "New package: packages/ratchet-pilot/"
echo "  incidents.py  — incident file parsing"
echo "  trust.py      — tier evaluation, regression triggers"
echo "  guardrails.py — preflight checks"
echo "  actions.py    — pause-and-ask queue"
echo "  metrics.py    — weekly metrics collection"
echo "  module.py     — PilotModule wiring"
echo ""
echo "Updated: agents/pawl/pawl.py (registers PilotModule)"
echo ""
echo "Run:"
echo "  pip install -e packages/ratchet-core -e packages/ratchet-memory -e packages/ratchet-pilot --force-reinstall --no-deps"
echo "  python agents/pawl/pawl.py"
