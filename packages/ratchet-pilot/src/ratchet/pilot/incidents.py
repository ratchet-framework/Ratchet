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
