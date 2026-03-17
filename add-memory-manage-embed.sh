#!/bin/bash
# Run from C:/Projects/Ratchet on the modularize branch
# Adds manage (lifecycle) and embed (semantic) to ratchet-memory
set -e

echo "🔧 Adding memory manage + embed pipelines..."

# --- manage.py ---
cat > packages/ratchet-memory/src/ratchet/memory/manage.py << 'PYEOF'
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
PYEOF

# --- embed.py ---
cat > packages/ratchet-memory/src/ratchet/memory/embed.py << 'PYEOF'
"""Semantic embedding pipeline for Ratchet Memory.

OpenAI text-embedding-3-small or local TF-IDF fallback.
Ported from reference-implementations/bin/memory-embed.
"""

import json
import logging
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib import request as urlreq

logger = logging.getLogger("ratchet.memory.embed")

EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


def fact_text(fact: dict[str, Any]) -> str:
    content = fact.get("content", "")
    tags = " ".join(fact.get("tags", []))
    category = fact.get("category", "")
    return f"{category}: {content} {tags}".strip()


def embed_openai(texts: list[str], api_key: str) -> list[list[float]]:
    payload = {"model": EMBED_MODEL, "input": texts}
    data = json.dumps(payload).encode("utf-8")
    req = urlreq.Request(
        "https://api.openai.com/v1/embeddings", data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urlreq.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return [item["embedding"] for item in sorted(result["data"], key=lambda x: x["index"])]


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def _build_vocab_and_idf(all_texts: list[str]) -> tuple[dict[str, int], dict[str, float]]:
    n = len(all_texts)
    df: dict[str, int] = {}
    for text in all_texts:
        for t in set(_tokenize(text)):
            df[t] = df.get(t, 0) + 1
    vocab = sorted(df.keys())
    vocab_index = {t: i for i, t in enumerate(vocab)}
    idf = {t: math.log(n / df[t]) + 1.0 for t in vocab}
    return vocab_index, idf


def _embed_tfidf_single(text: str, vocab_index: dict[str, int], idf: dict[str, float]) -> list[float]:
    tokens = _tokenize(text)
    tf: dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    total = max(len(tokens), 1)
    dim = len(vocab_index)
    vec = [0.0] * dim
    for t, count in tf.items():
        if t in vocab_index:
            vec[vocab_index[t]] = (count / total) * idf.get(t, 1.0)
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def embed_tfidf(texts: list[str], corpus_texts: list[str] | None = None) -> list[list[float]]:
    corpus = corpus_texts if corpus_texts else texts
    vocab_index, idf = _build_vocab_and_idf(corpus)
    return [_embed_tfidf_single(t, vocab_index, idf) for t in texts]


@dataclass
class EmbedResult:
    embedded_count: int = 0
    already_embedded: int = 0
    method: str = "tfidf"
    error: str | None = None


def embed_facts(memory_dir: Path | str, fact_id: str | None = None, dry_run: bool = False) -> EmbedResult:
    """Embed facts missing embeddings. OpenAI if key set, else TF-IDF."""
    memory_dir = Path(memory_dir)
    result = EmbedResult()

    all_facts = []
    for path in sorted(memory_dir.glob("facts-*.jsonl")):
        if "purged" in path.name:
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        all_facts.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    embeddings_file = memory_dir / "embeddings.json"
    existing = {}
    if embeddings_file.exists():
        with open(embeddings_file) as f:
            existing = json.load(f)

    if not all_facts:
        return result

    if fact_id:
        targets = [f for f in all_facts if f.get("id") == fact_id]
        if not targets:
            result.error = f"Fact ID {fact_id} not found"
            return result
    else:
        targets = [f for f in all_facts if f.get("id") not in existing]

    result.already_embedded = len(all_facts) - len(targets)

    if not targets:
        return result

    if dry_run:
        result.embedded_count = len(targets)
        result.method = "dry_run"
        return result

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    use_openai = bool(openai_key)
    result.method = "openai" if use_openai else "tfidf"

    texts = [fact_text(f) for f in targets]
    new_embeddings: dict[str, list[float]] = {}

    if use_openai:
        for i in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[i:i + BATCH_SIZE]
            batch_facts = targets[i:i + BATCH_SIZE]
            try:
                vectors = embed_openai(batch_texts, openai_key)
                for fact, vec in zip(batch_facts, vectors):
                    new_embeddings[fact["id"]] = vec
            except Exception as e:
                logger.warning(f"OpenAI failed ({e}), TF-IDF fallback")
                all_corpus = [fact_text(f) for f in all_facts]
                vecs = embed_tfidf(batch_texts, corpus_texts=all_corpus)
                for fact, vec in zip(batch_facts, vecs):
                    new_embeddings[fact["id"]] = vec
    else:
        all_corpus = [fact_text(f) for f in all_facts]
        vectors = embed_tfidf(texts, corpus_texts=all_corpus)
        for fact, vec in zip(targets, vectors):
            new_embeddings[fact["id"]] = vec

    existing.update(new_embeddings)
    memory_dir.mkdir(parents=True, exist_ok=True)
    with open(embeddings_file, "w") as f:
        json.dump(existing, f)

    result.embedded_count = len(new_embeddings)
    return result
PYEOF

# --- __init__.py (final exports) ---
cat > packages/ratchet-memory/src/ratchet/memory/__init__.py << 'PYEOF'
"""ratchet.memory — Persistent agent memory: extract, retrieve, manage, embed."""

from ratchet.memory.module import MemoryModule
from ratchet.memory.extract import ExtractionResult, extract_facts, append_facts_to_file
from ratchet.memory.retrieve import RetrievalResult, retrieve_facts, format_facts_for_injection, load_all_facts
from ratchet.memory.manage import ManageResult, Contradiction, manage_facts
from ratchet.memory.embed import EmbedResult, embed_facts, embed_tfidf, fact_text
from ratchet.memory.facts import validate_fact, credential_filter, normalize_fact, quarter_for_date
from ratchet.memory.scoring import effective_score, cosine_similarity
from ratchet.memory.providers import get_provider, AnthropicProvider, OpenAIProvider

__all__ = [
    "MemoryModule",
    "ExtractionResult", "extract_facts", "append_facts_to_file",
    "RetrievalResult", "retrieve_facts", "format_facts_for_injection", "load_all_facts",
    "ManageResult", "Contradiction", "manage_facts",
    "EmbedResult", "embed_facts", "embed_tfidf", "fact_text",
    "validate_fact", "credential_filter", "normalize_fact", "quarter_for_date",
    "effective_score", "cosine_similarity",
    "get_provider", "AnthropicProvider", "OpenAIProvider",
]
PYEOF

echo ""
echo "✅ Memory manage + embed added!"
echo ""
echo "New files:"
echo "  packages/ratchet-memory/src/ratchet/memory/manage.py  — promote, contradict, purge"
echo "  packages/ratchet-memory/src/ratchet/memory/embed.py   — OpenAI + TF-IDF embeddings"
echo ""
echo "Run:"
echo "  pip install -e packages/ratchet-core -e packages/ratchet-memory --force-reinstall --no-deps"
echo "  python agents/pawl/pawl.py"
