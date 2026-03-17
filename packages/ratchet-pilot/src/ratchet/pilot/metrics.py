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
