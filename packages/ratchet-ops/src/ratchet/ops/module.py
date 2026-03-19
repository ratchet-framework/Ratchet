"""OpsModule — business process automation for Ratchet agents.

Wires invoicing, expenses, and cost routing into the agent lifecycle:
  - Track API costs on every LLM call (via bus events)
  - Report spending summaries on heartbeat
  - Expose invoice parsing, expense tracking, and budget queries
"""

import logging
from pathlib import Path
from typing import Any, Optional

from ratchet.core.module import RatchetModule
from ratchet.ops.expenses import (
    BudgetSummary, Expense, load_expenses, record_expense, summarize_spending,
)
from ratchet.ops.invoicing import (
    Invoice, check_duplicate, load_invoices, parse_invoice_text, save_invoice,
)
from ratchet.ops.routing import (
    CostSummary, calculate_cost, log_cost, select_model, summarize_costs,
)

logger = logging.getLogger("ratchet.ops")


class OpsModule(RatchetModule):
    """
    Business process automation for Ratchet agents.

    Config keys (via context.json "ops" section):
        store_dir: str — directory for ops data (default: "ops")
        track_costs: bool — auto-log API costs from bus events (default: true)
        pricing: dict — override model pricing
    """

    name = "ops"
    version = "0.1.0"
    dependencies = ["pilot"]  # Trust tiers gate spending authority

    def __init__(self) -> None:
        self.agent = None
        self._store_dir: Path | None = None
        self._track_costs = True
        self._pricing: dict | None = None

    async def initialize(self, agent, config: dict[str, Any]) -> None:
        self.agent = agent
        store_rel = config.get("store_dir", "ops")
        self._store_dir = agent.workspace / store_rel
        self._store_dir.mkdir(parents=True, exist_ok=True)

        self._track_costs = config.get("track_costs", True)
        self._pricing = config.get("pricing")

        # Subscribe to cost-tracking events
        if self._track_costs:
            agent.bus.subscribe("ops.api_call", self._handle_api_call)

        logger.info(f"Ops initialized: store={self._store_dir}, cost_tracking={self._track_costs}")

    async def on_heartbeat(self) -> Optional[dict[str, Any]]:
        """Report spending and invoice stats."""
        stats: dict[str, Any] = {"status": "healthy"}

        # Cost summary
        costs = summarize_costs(self._store_dir, period="month")
        stats["monthly_cost"] = costs.total_cost
        stats["monthly_calls"] = costs.total_calls
        if costs.by_model:
            stats["top_model"] = list(costs.by_model.keys())[0]

        # Invoice stats
        invoices = load_invoices(self._store_dir)
        pending = [i for i in invoices if i.status == "pending"]
        stats["invoices_total"] = len(invoices)
        stats["invoices_pending"] = len(pending)

        # Expense summary
        spending = summarize_spending(self._store_dir, period="month")
        stats["monthly_expenses"] = spending.total

        return stats

    async def _handle_api_call(self, event_type: str, payload: dict[str, Any]) -> None:
        """Auto-log API costs from bus events."""
        model = payload.get("model", "")
        call_type = payload.get("call_type", "unknown")
        input_tokens = payload.get("input_tokens", 0)
        output_tokens = payload.get("output_tokens", 0)

        if model and (input_tokens or output_tokens):
            log_cost(model, call_type, input_tokens, output_tokens,
                    self._store_dir, self._pricing)

    # --- Public API ---

    def parse_invoice(self, text: str, source: str = "manual") -> Invoice:
        """Parse invoice text and check for duplicates."""
        invoice = parse_invoice_text(text)
        invoice.source = source

        dup = check_duplicate(invoice, self._store_dir)
        if dup:
            logger.warning(f"Duplicate invoice detected: {dup.vendor} ${dup.total}")
            invoice.status = "duplicate"

        save_invoice(invoice, self._store_dir)
        return invoice

    def add_expense(self, amount: float, vendor: str, category: str = "other",
                   description: str = "", recurring: bool = False) -> Expense:
        """Record a new expense."""
        expense = Expense(
            amount=amount, vendor=vendor, category=category,
            description=description, recurring=recurring,
        )
        record_expense(expense, self._store_dir)
        return expense

    def get_spending_summary(self, period: str = "month") -> BudgetSummary:
        """Get spending summary for a period."""
        return summarize_spending(self._store_dir, period)

    def get_cost_summary(self, period: str = "month") -> CostSummary:
        """Get API cost summary for a period."""
        return summarize_costs(self._store_dir, period)

    def route_model(self, task_description: str) -> str:
        """Select the best model for a task based on complexity."""
        return select_model(task_description)
