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
