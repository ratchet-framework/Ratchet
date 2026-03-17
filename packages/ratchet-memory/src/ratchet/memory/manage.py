"""Weekly lifecycle manager for Ratchet Memory.

Applies promotion, contradiction detection, and purge operations.
Stored importance is NEVER modified by decay — decay is retrieval-time only.

Ported from reference-implementations/bin/memory-manage.
"""

import json
import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ratchet.memory.scoring import effective_score

logger = logging.getLogger("ratchet.memory.manage")

PROMOTION_IMPORTANCE = 0.8
PROMOTION_REFS = 3
PURGE_THRESHOLD = 0.1

SWITCH_SIGNALS = ["switched", "changed", "now uses", "no longer", "stopped", "moved to", "replaced", "prefers now", "switched to", "changed to"]
PREFERENCE_SIGNALS = ["prefers", "uses", "likes", "favorite", "always", "typically"]


@dataclass
class Contradiction:
    fact_a: dict[str, Any]
    fact_b: dict[str, Any]
    reason: str


@dataclass
class ManageResult:
    total_facts: int = 0
    tier_counts: dict[str, int] = field(default_factory=dict)
    promoted: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    purged: list[dict[str, Any]] = field(default_factory=list)
    decayed_count: int = 0
    dry_run: bool = False


def _et_today() -> str:
    return datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d")


def _load_facts_from_file(path: Path) -> list[dict[str, Any]]:
    facts = []
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                facts.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"Skipping unparseable line {lineno} in {path}")
    return facts


def _load_all_facts_by_file(memory_dir: Path) -> dict[Path, list[dict[str, Any]]]:
    result = {}
    for path in sorted(memory_dir.glob("facts-*.jsonl")):
        if "purged" in path.name:
            continue
        result[path] = _load_facts_from_file(path)
    return result


def _detect_contradictions(all_facts: list[dict[str, Any]]) -> list[Contradiction]:
    contradictions = []
    for i, fa in enumerate(all_facts):
        tags_a = set(fa.get("tags", []))
        content_a = fa.get("content", "").lower()
        if not tags_a:
            continue
        for fb in all_facts[i + 1:]:
            tags_b = set(fb.get("tags", []))
            content_b = fb.get("content", "").lower()
            if not tags_b or not (tags_a & tags_b):
                continue
            if fa.get("superseded_by") or fb.get("superseded_by"):
                continue
            if fa.get("supersedes") and fb["id"] in str(fa.get("supersedes", "")):
                continue
            a_has_pref = any(s in content_a for s in PREFERENCE_SIGNALS)
            b_has_switch = any(s in content_b for s in SWITCH_SIGNALS)
            b_has_pref = any(s in content_b for s in PREFERENCE_SIGNALS)
            a_has_switch = any(s in content_a for s in SWITCH_SIGNALS)
            if (a_has_pref and b_has_switch) or (b_has_pref and a_has_switch):
                shared = list(tags_a & tags_b)
                contradictions.append(Contradiction(fact_a=fa, fact_b=fb,
                    reason=f"preference vs. change signal on shared tags: {shared}"))
    return contradictions


def _log_event(event_type: str, fact_id: str, detail: str, memory_dir: Path) -> None:
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event_type, "fact_id": fact_id, "detail": detail}
    with open(memory_dir / "memory-log.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def _remove_embeddings(fact_ids: list[str], memory_dir: Path) -> int:
    embeddings_file = memory_dir / "embeddings.json"
    if not fact_ids or not embeddings_file.exists():
        return 0
    with open(embeddings_file) as f:
        embeddings = json.load(f)
    removed = 0
    for fid in fact_ids:
        if fid in embeddings:
            del embeddings[fid]
            removed += 1
    if removed > 0:
        with open(embeddings_file, "w") as f:
            json.dump(embeddings, f)
    return removed


def manage_facts(memory_dir: Path | str, today: str | None = None, dry_run: bool = False) -> ManageResult:
    """Run weekly lifecycle: promote, detect contradictions, purge."""
    memory_dir = Path(memory_dir)
    if today is None:
        today = _et_today()

    result = ManageResult(dry_run=dry_run)
    facts_by_file = _load_all_facts_by_file(memory_dir)
    all_facts: list[dict[str, Any]] = []
    for facts in facts_by_file.values():
        all_facts.extend(facts)

    result.total_facts = len(all_facts)
    result.tier_counts = {
        "permanent": sum(1 for f in all_facts if f.get("tier") == "permanent"),
        "standard": sum(1 for f in all_facts if f.get("tier", "standard") == "standard"),
        "transient": sum(1 for f in all_facts if f.get("tier") == "transient"),
    }

    for fact in all_facts:
        fact["_effective_score"] = effective_score(fact, today)

    for fact in all_facts:
        if fact.get("promoted"):
            continue
        if fact.get("importance", 0) > PROMOTION_IMPORTANCE and fact.get("reference_count", 0) >= PROMOTION_REFS:
            result.promoted.append(fact)

    result.contradictions = _detect_contradictions(all_facts)

    for fact in all_facts:
        if fact.get("tier") == "permanent":
            continue
        if fact.get("_effective_score", fact.get("importance", 0)) < PURGE_THRESHOLD:
            result.purged.append(fact)

    result.decayed_count = sum(1 for f in all_facts if f.get("_effective_score", 1) < f.get("importance", 1))

    if not dry_run:
        purge_ids = {f["id"] for f in result.purged}
        promoted_ids = {f["id"] for f in result.promoted}

        for path, file_facts in facts_by_file.items():
            new_lines = []
            updated = False
            for fact in file_facts:
                fid = fact.get("id")
                if fid in purge_ids:
                    updated = True
                    continue
                if fid in promoted_ids and not fact.get("promoted"):
                    fact["promoted"] = True
                    updated = True
                fact["last_managed"] = today
                updated = True
                fact.pop("_effective_score", None)
                fact.pop("_decay_weeks", None)
                new_lines.append(fact)

            if updated:
                import os
                fd, tmp_path = tempfile.mkstemp(dir=str(memory_dir), prefix="facts-tmp-")
                try:
                    with os.fdopen(fd, "w") as f:
                        for fact in new_lines:
                            f.write(json.dumps(fact) + "\n")
                    shutil.move(tmp_path, str(path))
                except Exception:
                    os.unlink(tmp_path)
                    raise

        if result.purged:
            with open(memory_dir / "facts-purged.jsonl", "a") as f:
                for fact in result.purged:
                    fact.pop("_effective_score", None)
                    f.write(json.dumps(fact) + "\n")
            for f in result.purged:
                _log_event("purged", f["id"], f"importance={f.get('importance', 0):.3f}", memory_dir)

        purge_id_list = [f["id"] for f in result.purged]
        superseded_ids = [f["id"] for f in all_facts if f.get("superseded_by")]
        _remove_embeddings(list(set(purge_id_list + superseded_ids)), memory_dir)

        for f in result.promoted:
            _log_event("promoted", f["id"], f"importance={f.get('importance', 0):.3f} ref_count={f.get('reference_count', 0)}", memory_dir)

    return result
