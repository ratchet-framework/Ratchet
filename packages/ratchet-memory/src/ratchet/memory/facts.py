"""Fact schema, validation, and credential filtering.

This is the data layer — no LLM calls, no I/O, just pure validation logic.
Ported from reference-implementations/bin/memory-extract.
"""

import json
import re
import uuid
from datetime import datetime
from typing import Any

# --- Schema ---

ALLOWED_CATEGORIES = [
    "vehicle", "incident", "decision", "preference",
    "process", "person", "project", "system",
]

ALLOWED_TIERS = ["permanent", "standard", "transient"]

REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "id": str,
    "content": str,
    "category": str,
    "importance": (int, float),
    "tier": str,
    "created": str,
    "source_session": str,
    "tags": list,
}

OPTIONAL_FIELDS_WITH_DEFAULTS: dict[str, Any] = {
    "last_referenced": None,
    "reference_count": 0,
    "supersedes": None,
    "superseded_by": None,
    "promoted": False,
    "source_trust": "trusted",
}

DEFAULT_IMPORTANCE: dict[str, float] = {
    "incident": 0.9, "decision": 0.9, "vehicle": 0.8,
    "preference": 0.6, "process": 0.6, "person": 0.6,
    "project": 0.6, "system": 0.6, "casual": 0.3,
}

# --- Patterns ---

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
LONG_ALNUM_RE = re.compile(r"[A-Za-z0-9_\-]{20,}")

CREDENTIAL_PATTERNS = [
    r"sk-ant-api[0-9a-zA-Z-]+",
    r"sk-proj-[0-9a-zA-Z-]+",
    r"ghp_[0-9a-zA-Z]+",
    r"xoxb-[0-9a-zA-Z-]+",
    r"AIza[0-9a-zA-Z-_]+",
    r"password\s*[:=]\s*\S+",
    r"token\s*[:=]\s*[a-zA-Z0-9_\-\.]{20,}",
    r"api.?key\s*[:=]\s*\S+",
    r"secret\s*[:=]\s*\S+",
]

CREDENTIAL_KEYWORDS = ["sk-", "ghp_", "api key", "password", "token", "secret_key"]
CREDENTIAL_PATH_PATTERNS = [r"\.env\b", r"secrets/", r"\.openclaw/secrets/"]

PERMANENT_KEYWORDS = ["always remember", "never forget", "permanent"]
TRANSIENT_KEYWORDS = ["temporary", "just for now", "this session"]
REMEMBER_KEYWORDS = ["remember this", "always remember", "never forget", "permanent"]
ACTION_KEYWORDS = ["overdue", "urgent", "action required", "order", "fix"]


def quarter_for_date(date_str: str) -> str:
    """Return 'YYYY-Q#' for a date string like '2026-02-28'."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        d = datetime.now()
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def new_fact_id() -> str:
    return str(uuid.uuid4())


def validate_fact(fact: dict[str, Any]) -> tuple[bool, str]:
    """Validate a fact dict. Returns (True, '') or (False, reason)."""
    if not isinstance(fact, dict):
        return False, "not a dict"

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in fact:
            return False, f"missing required field: {field}"
        val = fact[field]
        types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
        if not isinstance(val, types):
            return False, f"field '{field}' has wrong type: expected {expected_type}, got {type(val).__name__}"

    if not fact["id"] or not UUID_RE.match(str(fact["id"])):
        return False, f"invalid id (not UUID format): {str(fact['id'])[:40]}"
    if not fact["content"] or len(fact["content"].strip()) < 10:
        return False, f"content too short ({len(fact.get('content', ''))} chars, need >= 10)"
    if fact["category"] not in ALLOWED_CATEGORIES:
        return False, f"invalid category: {fact['category']}"
    imp = fact["importance"]
    if not (0.0 <= float(imp) <= 1.0):
        return False, f"importance out of range: {imp}"
    if fact["tier"] not in ALLOWED_TIERS:
        return False, f"invalid tier: {fact['tier']}"
    if not DATE_RE.match(fact["created"]):
        return False, f"invalid created date: {fact['created']}"
    if not fact["source_session"]:
        return False, "empty source_session"
    if not isinstance(fact["tags"], list):
        return False, "tags is not a list"
    for t in fact["tags"]:
        if not isinstance(t, str):
            return False, f"tag is not a string: {t}"

    return True, ""


def credential_filter(fact: dict[str, Any]) -> bool:
    """Return True if a fact should be REJECTED due to credential-like content."""
    content = fact.get("content", "")
    text = json.dumps(fact)

    for pattern in CREDENTIAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    content_lower = content.lower()
    for kw in CREDENTIAL_KEYWORDS:
        if kw in content_lower:
            return True

    for pattern in CREDENTIAL_PATH_PATTERNS:
        if re.search(pattern, content):
            return True

    for match in LONG_ALNUM_RE.finditer(content):
        token = match.group()
        if UUID_RE.match(token):
            continue
        has_upper = any(c.isupper() for c in token)
        has_lower = any(c.islower() for c in token)
        has_digit = any(c.isdigit() for c in token)
        if has_upper and has_lower and has_digit and len(token) > 24:
            return True

    return False


def normalize_fact(fact: dict[str, Any], session_date: str) -> dict[str, Any]:
    """Apply defaults, normalize fields, enforce tier/importance modifiers."""
    fact.setdefault("id", new_fact_id())
    fact.setdefault("tags", [])
    fact.setdefault("tier", "standard")
    fact.setdefault("created", session_date)
    fact.setdefault("source_session", session_date)

    if fact.get("category") and fact["category"] not in ALLOWED_CATEGORIES:
        fact["category"] = "system"

    try:
        fact["importance"] = float(fact.get("importance", 0.5))
    except (ValueError, TypeError):
        fact["importance"] = 0.5

    for field, default in OPTIONAL_FIELDS_WITH_DEFAULTS.items():
        if field == "last_referenced":
            fact.setdefault(field, fact["created"])
        else:
            fact.setdefault(field, default)

    content_lower = fact["content"].lower()
    if any(kw in content_lower for kw in PERMANENT_KEYWORDS):
        fact["tier"] = "permanent"
    elif any(kw in content_lower for kw in TRANSIENT_KEYWORDS):
        fact["tier"] = "transient"

    imp = float(fact["importance"])
    if any(kw in content_lower for kw in REMEMBER_KEYWORDS):
        imp = min(1.0, imp + 0.2)
    if any(kw in content_lower for kw in ACTION_KEYWORDS):
        imp = min(1.0, imp + 0.15)
    fact["importance"] = max(0.0, min(1.0, imp))

    return fact
