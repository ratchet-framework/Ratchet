"""Expense tracking and categorization.

Records expenses with categories, tracks spending by period,
and provides budget summaries.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("ratchet.ops.expenses")

DEFAULT_CATEGORIES = [
    "infrastructure", "api_credits", "domains", "software",
    "hardware", "services", "office", "travel", "other",
]


@dataclass
class Expense:
    """A tracked expense."""
    id: str = ""
    amount: float = 0.0
    currency: str = "USD"
    category: str = "other"
    vendor: str = ""
    description: str = ""
    date: str = ""
    recurring: bool = False
    recurring_interval: str = ""  # monthly, annual, etc.
    invoice_id: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class BudgetSummary:
    """Spending summary for a period."""
    period: str = ""
    total: float = 0.0
    by_category: dict[str, float] = field(default_factory=dict)
    by_vendor: dict[str, float] = field(default_factory=dict)
    count: int = 0
    recurring_total: float = 0.0


def _today() -> str:
    return datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d")


def record_expense(expense: Expense, store_dir: Path | str) -> Path:
    """Append an expense to the JSONL store."""
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    store_file = store_dir / "expenses.jsonl"

    if not expense.id:
        expense.id = str(uuid.uuid4())
    if not expense.date:
        expense.date = _today()

    data = {
        "id": expense.id,
        "amount": expense.amount,
        "currency": expense.currency,
        "category": expense.category,
        "vendor": expense.vendor,
        "description": expense.description,
        "date": expense.date,
        "recurring": expense.recurring,
        "recurring_interval": expense.recurring_interval,
        "invoice_id": expense.invoice_id,
        "tags": expense.tags,
    }

    with open(store_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")

    logger.info(f"Recorded expense: ${expense.amount:.2f} to {expense.vendor} ({expense.category})")
    return store_file


def load_expenses(
    store_dir: Path | str,
    category: str | None = None,
    since: str | None = None,
) -> list[Expense]:
    """Load expenses, optionally filtered by category or date."""
    store_dir = Path(store_dir)
    store_file = store_dir / "expenses.jsonl"
    if not store_file.exists():
        return []

    expenses = []
    with open(store_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                exp = Expense(**{k: v for k, v in data.items() if k in Expense.__dataclass_fields__})
                if category and exp.category != category:
                    continue
                if since and exp.date < since:
                    continue
                expenses.append(exp)
            except (json.JSONDecodeError, TypeError):
                pass

    return expenses


def summarize_spending(
    store_dir: Path | str,
    period: str = "month",
) -> BudgetSummary:
    """
    Summarize spending for a period.

    Args:
        store_dir: Expense store directory.
        period: "week", "month", "quarter", or "year".
    """
    now = datetime.now(timezone(timedelta(hours=-5)))
    if period == "week":
        since = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period == "month":
        since = now.replace(day=1).strftime("%Y-%m-%d")
    elif period == "quarter":
        q_month = ((now.month - 1) // 3) * 3 + 1
        since = now.replace(month=q_month, day=1).strftime("%Y-%m-%d")
    elif period == "year":
        since = now.replace(month=1, day=1).strftime("%Y-%m-%d")
    else:
        since = None

    expenses = load_expenses(store_dir, since=since)

    summary = BudgetSummary(period=period, count=len(expenses))

    for exp in expenses:
        summary.total += exp.amount
        summary.by_category[exp.category] = summary.by_category.get(exp.category, 0) + exp.amount
        summary.by_vendor[exp.vendor] = summary.by_vendor.get(exp.vendor, 0) + exp.amount
        if exp.recurring:
            summary.recurring_total += exp.amount

    summary.total = round(summary.total, 2)
    summary.recurring_total = round(summary.recurring_total, 2)
    summary.by_category = {k: round(v, 2) for k, v in sorted(summary.by_category.items(), key=lambda x: -x[1])}
    summary.by_vendor = {k: round(v, 2) for k, v in sorted(summary.by_vendor.items(), key=lambda x: -x[1])}

    return summary
