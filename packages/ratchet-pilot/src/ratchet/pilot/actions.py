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
