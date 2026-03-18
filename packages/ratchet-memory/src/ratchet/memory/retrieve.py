"""Fact retrieval pipeline.

Three strategies: score-only, LLM-selected, embedding-based.
Ported from reference-implementations/bin/memory-retrieve.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ratchet.memory.providers import LLMProvider
from ratchet.memory.scoring import cosine_similarity, effective_score

logger = logging.getLogger("ratchet.memory.retrieve")

EMBEDDING_THRESHOLD = 50
MAX_OUTPUT_WORDS = 1400

RETRIEVAL_SYSTEM_PROMPT = """You are a context selector for an AI agent.

Given a list of facts from previous sessions and the current session's opening context,
select the 10-15 facts most relevant and useful for the current session.

Prioritize:
1. Facts directly relevant to the current context/topic
2. High-importance facts (incidents, decisions, vehicles)
3. Recently referenced or created facts
4. Facts that might prevent mistakes or surface important context

Return ONLY a JSON array of fact IDs (the "id" field values), like:
["uuid1", "uuid2", "uuid3", ...]

No explanation, no markdown, just the JSON array."""


@dataclass
class RetrievalResult:
    facts: list[dict[str, Any]] = field(default_factory=list)
    strategy: str = "score"
    total_available: int = 0
    error: str | None = None

    @property
    def count(self) -> int:
        return len(self.facts)


def _et_today() -> str:
    return datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d")


def load_all_facts(memory_dir: Path | str) -> list[dict[str, Any]]:
    memory_dir = Path(memory_dir)
    facts = []
    for path in sorted(memory_dir.glob("facts-*.jsonl")):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    facts.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return facts


def load_embeddings(memory_dir: Path | str) -> dict[str, list[float]]:
    embeddings_file = Path(memory_dir) / "embeddings.json"
    if not embeddings_file.exists():
        return {}
    with open(embeddings_file) as f:
        return json.load(f)


def _embed_query_openai(text: str, api_key: str) -> list[float]:
    from urllib import request as urlreq
    payload = {"model": "text-embedding-3-small", "input": [text]}
    data = json.dumps(payload).encode("utf-8")
    req = urlreq.Request(
        "https://api.openai.com/v1/embeddings", data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urlreq.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["data"][0]["embedding"]


def _select_by_score(scored_facts, top_n):
    return scored_facts[:top_n]


def _select_by_llm(scored_facts, context, top_n, provider):
    candidates = scored_facts[:150]
    facts_text = []
    for fact in candidates:
        if not fact.get("id") or not fact.get("content"):
            continue
        facts_text.append(json.dumps({
            "id": fact["id"], "content": fact["content"],
            "category": fact.get("category", "?"),
            "importance": round(fact.get("importance", 0.5), 1),
            "created": fact.get("created", "?"),
            "last_referenced": fact.get("last_referenced", "?"),
            "tags": fact.get("tags", []),
        }))

    user_message = f"""Opening context for this session: "{context}"

Facts from previous sessions (top {len(candidates)} by importance x recency):
{chr(10).join(facts_text)}

Select the {top_n}-15 most relevant fact IDs for this session."""

    raw = provider.complete(RETRIEVAL_SYSTEM_PROMPT, user_message)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])

    selected_ids = json.loads(raw.strip())
    id_to_fact = {f["id"]: f for f in candidates}
    selected = [id_to_fact[fid] for fid in selected_ids if fid in id_to_fact]

    if len(selected) < min(top_n, len(candidates)):
        used_ids = {f["id"] for f in selected}
        for f in candidates:
            if len(selected) >= top_n:
                break
            if f["id"] not in used_ids:
                selected.append(f)
    return selected


def _select_by_embeddings(scored_facts, context, top_n, embeddings, openai_api_key):
    if not openai_api_key:
        return None

    query_vec = _embed_query_openai(context, openai_api_key)
    scored = []
    for fact in scored_facts:
        fid = fact.get("id")
        if fid not in embeddings:
            continue
        sim = cosine_similarity(query_vec, embeddings[fid])
        combined = sim * fact.get("_score", 0.5)
        scored.append((combined, fact))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [f for _, f in scored[:top_n]]

    if len(results) < min(top_n, len(scored_facts)):
        used_ids = {f["id"] for f in results}
        for f in scored_facts:
            if len(results) >= top_n:
                break
            if f["id"] not in used_ids:
                results.append(f)
    return results


def format_facts_for_injection(facts: list[dict[str, Any]]) -> str:
    if not facts:
        return "No relevant facts from previous sessions."

    lines = ["## Known context from previous sessions", ""]
    for fact in facts:
        cat = fact.get("category", "?").upper()
        content = fact.get("content", "")
        created = fact.get("created", "?")
        last_ref = fact.get("last_referenced", "?")
        date_info = f"(created {created}, last referenced {last_ref})" if last_ref != created else f"(from {created})"
        lines.append(f"- **[{cat}]** {content} {date_info}")

    lines.append("")
    text = "\n".join(lines)
    words = text.split()
    if len(words) > MAX_OUTPUT_WORDS:
        text = " ".join(words[:MAX_OUTPUT_WORDS]) + "\n\n[... truncated for token budget]"
    return text


def retrieve_facts(
    memory_dir: Path | str,
    context: str | None = None,
    top_n: int = 15,
    provider: LLMProvider | None = None,
    today: str | None = None,
    force_strategy: str | None = None,
) -> RetrievalResult:
    """Retrieve most relevant facts for a session."""
    memory_dir = Path(memory_dir)
    if today is None:
        today = _et_today()

    all_facts = load_all_facts(memory_dir)
    if not all_facts:
        return RetrievalResult(total_available=0)

    for fact in all_facts:
        fact["_score"] = effective_score(fact, today)
    all_facts.sort(key=lambda f: f["_score"], reverse=True)

    result = RetrievalResult(total_available=len(all_facts))

    if force_strategy == "score" or not context:
        result.facts = _select_by_score(all_facts, top_n)
        result.strategy = "score"
        return result

    if force_strategy == "embedding" or force_strategy is None:
        embeddings = load_embeddings(memory_dir)
        if len(embeddings) >= EMBEDDING_THRESHOLD or force_strategy == "embedding":
            openai_key = os.environ.get("OPENAI_API_KEY", "")
            try:
                embed_results = _select_by_embeddings(all_facts, context, top_n, embeddings, openai_key)
                if embed_results is not None:
                    result.facts = embed_results
                    result.strategy = "embedding"
                    return result
            except Exception as e:
                if force_strategy == "embedding":
                    result.error = str(e)
                    return result

    if provider is not None:
        try:
            result.facts = _select_by_llm(all_facts, context, top_n, provider)
            result.strategy = "llm"
            return result
        except Exception as e:
            logger.warning(f"LLM selection failed: {e}, falling back to score")

    result.facts = _select_by_score(all_facts, top_n)
    result.strategy = "score"
    return result
