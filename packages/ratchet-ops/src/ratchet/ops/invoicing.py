"""Invoice parsing, storage, and duplicate detection.

Rule-based extraction with LLM fallback for low-confidence parses.
Duplicate detection uses vendor+invoice_number+total as primary key.
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("ratchet.ops.invoicing")


@dataclass
class Invoice:
    """A parsed invoice."""
    id: str = ""
    vendor: str = ""
    invoice_number: str = ""
    date: str = ""
    total: float = 0.0
    currency: str = "USD"
    line_items: list[dict[str, Any]] = field(default_factory=list)
    status: str = "pending"  # pending, approved, paid, rejected
    category: str = ""
    source: str = ""  # email, upload, manual
    raw_text: str = ""
    parsed_at: str = ""
    confidence: float = 0.0


def _today() -> str:
    return datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d")


# --- Rule-based extraction ---

_AMOUNT_RE = re.compile(r"\$\s*([\d,]+\.?\d*)")
_INVOICE_NUM_RE = re.compile(r"(?:invoice|inv|receipt|order)\s*#?\s*[:.]?\s*([A-Z0-9][\w-]{2,20})", re.IGNORECASE)
_DATE_RE = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})")
_VENDOR_PATTERNS = [
    (r"(?:from|vendor|billed by|company)\s*[:.]?\s*(.+)", re.IGNORECASE),
]


def parse_invoice_text(text: str) -> Invoice:
    """
    Extract invoice fields from text using rule-based patterns.

    Returns an Invoice with confidence score (0.0-1.0) based on
    how many fields were successfully extracted.
    """
    inv = Invoice(
        id=str(uuid.uuid4()),
        raw_text=text[:5000],
        parsed_at=_today(),
    )

    fields_found = 0

    # Total amount
    amounts = _AMOUNT_RE.findall(text)
    if amounts:
        # Take the largest amount as the total
        parsed = [float(a.replace(",", "")) for a in amounts]
        inv.total = max(parsed)
        fields_found += 1

    # Invoice number
    m = _INVOICE_NUM_RE.search(text)
    if m:
        inv.invoice_number = m.group(1).strip()
        fields_found += 1

    # Date
    dates = _DATE_RE.findall(text)
    if dates:
        inv.date = dates[0]
        fields_found += 1

    # Vendor (try patterns, fall back to first line)
    for pattern, flags in _VENDOR_PATTERNS:
        m = re.search(pattern, text, flags)
        if m:
            inv.vendor = m.group(1).strip()[:100]
            fields_found += 1
            break
    if not inv.vendor:
        first_line = text.strip().split("\n")[0].strip()[:100]
        if first_line and len(first_line) < 80:
            inv.vendor = first_line

    inv.confidence = min(1.0, fields_found / 4.0)
    return inv


# --- Storage ---

def save_invoice(invoice: Invoice, store_dir: Path | str) -> Path:
    """Append an invoice to the JSONL store."""
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    store_file = store_dir / "invoices.jsonl"

    data = {
        "id": invoice.id,
        "vendor": invoice.vendor,
        "invoice_number": invoice.invoice_number,
        "date": invoice.date,
        "total": invoice.total,
        "currency": invoice.currency,
        "line_items": invoice.line_items,
        "status": invoice.status,
        "category": invoice.category,
        "source": invoice.source,
        "parsed_at": invoice.parsed_at,
        "confidence": invoice.confidence,
    }

    with open(store_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")

    return store_file


def load_invoices(store_dir: Path | str, status: str | None = None) -> list[Invoice]:
    """Load invoices from JSONL store, optionally filtered by status."""
    store_dir = Path(store_dir)
    store_file = store_dir / "invoices.jsonl"
    if not store_file.exists():
        return []

    invoices = []
    with open(store_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                inv = Invoice(**{k: v for k, v in data.items() if k in Invoice.__dataclass_fields__})
                if status is None or inv.status == status:
                    invoices.append(inv)
            except (json.JSONDecodeError, TypeError):
                pass

    return invoices


def check_duplicate(invoice: Invoice, store_dir: Path | str) -> Invoice | None:
    """
    Check if an invoice is a duplicate.

    Primary key: vendor + invoice_number + total
    Fallback: vendor + date + total
    """
    existing = load_invoices(store_dir)

    for e in existing:
        # Primary: vendor + invoice_number + total
        if (e.vendor.lower() == invoice.vendor.lower()
                and e.invoice_number == invoice.invoice_number
                and e.invoice_number
                and abs(e.total - invoice.total) < 0.01):
            return e

        # Fallback: vendor + date + total
        if (e.vendor.lower() == invoice.vendor.lower()
                and e.date == invoice.date
                and e.date
                and abs(e.total - invoice.total) < 0.01):
            return e

    return None
