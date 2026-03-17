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
