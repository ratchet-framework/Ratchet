"""Research storage — persist and retrieve research results.

Stores research entries as JSONL with optional vector embeddings
for semantic retrieval of past research.
"""

import json
import logging
import math
import os
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import request as urlreq

logger = logging.getLogger("ratchet.research.store")


@dataclass
class ResearchEntry:
    """A stored research result."""
    id: str = ""
    question: str = ""
    summary: str = ""
    full_text: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    confidence: str = "medium"
    created: str = ""
    tags: list[str] = field(default_factory=list)


def _today() -> str:
    return datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d")


def save_research(
    entry: ResearchEntry,
    store_dir: Path | str,
) -> Path:
    """Append a research entry to the JSONL store."""
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)

    if not entry.id:
        entry.id = str(uuid.uuid4())
    if not entry.created:
        entry.created = _today()

    store_file = store_dir / "research.jsonl"
    data = {
        "id": entry.id,
        "question": entry.question,
        "summary": entry.summary,
        "full_text": entry.full_text,
        "sources": entry.sources,
        "confidence": entry.confidence,
        "created": entry.created,
        "tags": entry.tags,
    }

    with open(store_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")

    logger.info(f"Saved research: {entry.question[:60]}")
    return store_file


def load_research(
    store_dir: Path | str,
    query: str | None = None,
    limit: int = 20,
) -> list[ResearchEntry]:
    """
    Load research entries from the JSONL store.

    If query is provided, filter by keyword match in question + summary.
    """
    store_dir = Path(store_dir)
    store_file = store_dir / "research.jsonl"

    if not store_file.exists():
        return []

    entries = []
    with open(store_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(ResearchEntry(**{
                    k: v for k, v in data.items()
                    if k in ResearchEntry.__dataclass_fields__
                }))
            except (json.JSONDecodeError, TypeError):
                pass

    if query:
        query_lower = query.lower()
        entries = [
            e for e in entries
            if query_lower in e.question.lower() or query_lower in e.summary.lower()
            or any(query_lower in t.lower() for t in e.tags)
        ]

    # Most recent first
    entries.sort(key=lambda e: e.created, reverse=True)
    return entries[:limit]


# --- Vector search (optional) ---

def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def _tfidf_embed(text: str, vocab: dict[str, int], idf: dict[str, float]) -> list[float]:
    tokens = _tokenize(text)
    tf: dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    total = max(len(tokens), 1)
    vec = [0.0] * len(vocab)
    for t, count in tf.items():
        if t in vocab:
            vec[vocab[t]] = (count / total) * idf.get(t, 1.0)
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na * nb > 0 else 0.0


def search_research(
    query: str,
    store_dir: Path | str,
    top_n: int = 5,
) -> list[tuple[float, ResearchEntry]]:
    """
    Semantic search over stored research using TF-IDF.

    Returns list of (similarity_score, entry) tuples sorted by relevance.
    """
    entries = load_research(store_dir, limit=500)
    if not entries:
        return []

    # Build corpus
    corpus_texts = [f"{e.question} {e.summary} {' '.join(e.tags)}" for e in entries]
    all_texts = corpus_texts + [query]

    # Build vocab + IDF
    n = len(all_texts)
    df: dict[str, int] = {}
    for text in all_texts:
        for t in set(_tokenize(text)):
            df[t] = df.get(t, 0) + 1
    vocab = {t: i for i, t in enumerate(sorted(df.keys()))}
    idf = {t: math.log(n / df[t]) + 1.0 for t in vocab}

    # Embed query
    query_vec = _tfidf_embed(query, vocab, idf)

    # Score entries
    scored = []
    for entry, text in zip(entries, corpus_texts):
        entry_vec = _tfidf_embed(text, vocab, idf)
        sim = _cosine_sim(query_vec, entry_vec)
        scored.append((sim, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_n]
