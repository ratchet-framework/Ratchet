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
