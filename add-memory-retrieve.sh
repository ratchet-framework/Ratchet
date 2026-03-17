#!/bin/bash
# Run from C:/Projects/Ratchet on the modularize branch
# Adds the retrieval pipeline to ratchet-memory
set -e

echo "🔍 Adding memory retrieval pipeline..."

# --- scoring.py ---
cat > packages/ratchet-memory/src/ratchet/memory/scoring.py << 'PYEOF'
"""Fact scoring — decay, recency, and effective score computation.

Used at retrieval time to rank facts by relevance. Scores are
computed on the fly and never written back to storage.
"""

import math
from datetime import datetime
from typing import Any

DECAY_STANDARD = 0.95
DECAY_TRANSIENT = 0.80


def days_since(date_str: str, today_str: str) -> int:
    try:
        d1 = datetime.strptime(date_str, "%Y-%m-%d")
        d2 = datetime.strptime(today_str, "%Y-%m-%d")
        return max(0, (d2 - d1).days)
    except (ValueError, TypeError):
        return 30


def effective_score(fact: dict[str, Any], today: str) -> float:
    """Score = stored_importance x decay_factor (tier-dependent)."""
    base = float(fact.get("importance", 0.5))
    last_ref = fact.get("last_referenced") or fact.get("created") or today
    weeks = days_since(last_ref, today) / 7.0
    tier = fact.get("tier", "standard")

    if tier == "permanent":
        return base
    if fact.get("superseded_by"):
        return 0.01
    if tier == "transient":
        return base * (DECAY_TRANSIENT ** weeks)
    return base * (DECAY_STANDARD ** weeks)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    denom = norm_a * norm_b
    return dot / denom if denom > 0 else 0.0
PYEOF

# --- retrieve.py ---
cat > packages/ratchet-memory/src/ratchet/memory/retrieve.py << 'PYEOF'
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
PYEOF

# --- module.py (updated with retrieval) ---
cat > packages/ratchet-memory/src/ratchet/memory/module.py << 'PYEOF'
"""MemoryModule — Ratchet's persistent memory system.

Full lifecycle: Extract, Retrieve, Manage (TODO), Embed (TODO).
"""

import logging
from pathlib import Path
from typing import Any, Optional

from ratchet.core.module import RatchetModule
from ratchet.memory.extract import ExtractionResult, append_facts_to_file, extract_facts
from ratchet.memory.facts import quarter_for_date
from ratchet.memory.providers import get_provider, LLMProvider
from ratchet.memory.retrieve import RetrievalResult, format_facts_for_injection, retrieve_facts

logger = logging.getLogger("ratchet.memory")


class MemoryModule(RatchetModule):
    """
    Persistent agent memory.

    Config keys (via context.json "memory" section):
        facts_dir: str — directory for facts JSONL (default: "memory/facts")
        provider: str — LLM provider ("anthropic", "openai")
        provider_model: str — model override
        max_retrieval: int — max facts at session start (default: 15)
    """

    name = "memory"
    version = "0.2.0"

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.agent = None
        self._provider = provider
        self._facts_dir: Path | None = None
        self._max_retrieval = 15
        self._last_extraction: ExtractionResult | None = None
        self._last_retrieval: RetrievalResult | None = None

    async def initialize(self, agent, config: dict[str, Any]) -> None:
        self.agent = agent
        facts_rel = config.get("facts_dir", "memory/facts")
        self._facts_dir = agent.workspace / facts_rel
        self._facts_dir.mkdir(parents=True, exist_ok=True)

        if self._provider is None:
            provider_name = config.get("provider", "anthropic")
            provider_kwargs = {}
            if "provider_model" in config:
                provider_kwargs["model"] = config["provider_model"]
            self._provider = get_provider(provider_name, **provider_kwargs)

        self._max_retrieval = config.get("max_retrieval", 15)
        agent.bus.subscribe("agent.session_end", self._handle_session_end)
        logger.info(f"Memory initialized: provider={self._provider.name}, facts_dir={self._facts_dir}")

    async def on_session_start(self, context: dict[str, Any]) -> None:
        opening_context = context.get("context", context.get("topic", ""))
        result = retrieve_facts(
            memory_dir=self._facts_dir,
            context=opening_context or None,
            top_n=self._max_retrieval,
            provider=self._provider,
        )
        self._last_retrieval = result

        if result.facts:
            context["memory_facts"] = result.facts
            context["memory_context"] = format_facts_for_injection(result.facts)
            await self.agent.bus.publish("memory.facts_retrieved", {
                "count": result.count, "strategy": result.strategy,
                "total_available": result.total_available,
            })
            logger.info(f"Injected {result.count} facts (strategy: {result.strategy})")
        else:
            context["memory_facts"] = []
            context["memory_context"] = ""

    async def on_session_end(self, context: dict[str, Any]) -> None:
        transcript = context.get("transcript", "")
        session_date = context.get("session_date", "")
        if not transcript:
            return
        if not session_date:
            from datetime import datetime, timedelta, timezone as tz
            session_date = datetime.now(tz(timedelta(hours=-5))).strftime("%Y-%m-%d")

        result = extract_facts(
            transcript=transcript, session_date=session_date,
            provider=self._provider, memory_dir=self._facts_dir,
        )
        self._last_extraction = result

        if result.facts:
            quarter = quarter_for_date(session_date)
            append_facts_to_file(result.facts, quarter, self._facts_dir)
            await self.agent.bus.publish("memory.facts_extracted", {
                "count": result.count, "session_date": session_date, "quarter": quarter,
                "rejected_validation": result.rejected_validation,
                "rejected_credentials": result.rejected_credentials,
            })

    async def on_heartbeat(self) -> Optional[dict[str, Any]]:
        stats: dict[str, Any] = {
            "status": "healthy",
            "provider": self._provider.name if self._provider else "none",
            "facts_dir": str(self._facts_dir),
        }
        if self._facts_dir and self._facts_dir.exists():
            total = 0
            for f in self._facts_dir.glob("facts-*.jsonl"):
                with open(f) as fh:
                    total += sum(1 for line in fh if line.strip())
            stats["total_facts"] = total
        if self._last_retrieval:
            stats["last_retrieval"] = {"count": self._last_retrieval.count, "strategy": self._last_retrieval.strategy}
        if self._last_extraction:
            stats["last_extraction"] = {
                "count": self._last_extraction.count,
                "rejected": self._last_extraction.rejected_validation + self._last_extraction.rejected_credentials,
            }
        return stats

    async def _handle_session_end(self, event_type: str, payload: dict[str, Any]) -> None:
        await self.on_session_end(payload)

    def extract_from_transcript(self, transcript: str, session_date: str) -> ExtractionResult:
        return extract_facts(transcript=transcript, session_date=session_date,
                           provider=self._provider, memory_dir=self._facts_dir)

    def retrieve_for_context(self, context: str | None = None, top_n: int | None = None) -> RetrievalResult:
        return retrieve_facts(memory_dir=self._facts_dir, context=context,
                            top_n=top_n or self._max_retrieval, provider=self._provider)
PYEOF

# --- __init__.py (updated exports) ---
cat > packages/ratchet-memory/src/ratchet/memory/__init__.py << 'PYEOF'
"""ratchet.memory — Persistent agent memory with fact extraction and retrieval."""

from ratchet.memory.module import MemoryModule
from ratchet.memory.extract import ExtractionResult, extract_facts, append_facts_to_file
from ratchet.memory.retrieve import RetrievalResult, retrieve_facts, format_facts_for_injection, load_all_facts
from ratchet.memory.facts import validate_fact, credential_filter, normalize_fact, quarter_for_date
from ratchet.memory.scoring import effective_score, cosine_similarity
from ratchet.memory.providers import get_provider, AnthropicProvider, OpenAIProvider

__all__ = [
    "MemoryModule",
    "ExtractionResult", "extract_facts", "append_facts_to_file",
    "RetrievalResult", "retrieve_facts", "format_facts_for_injection", "load_all_facts",
    "validate_fact", "credential_filter", "normalize_fact", "quarter_for_date",
    "effective_score", "cosine_similarity",
    "get_provider", "AnthropicProvider", "OpenAIProvider",
]
PYEOF

echo ""
echo "✅ Memory retrieval pipeline added!"
echo ""
echo "New files:"
echo "  packages/ratchet-memory/src/ratchet/memory/scoring.py   — decay, recency, effective score"
echo "  packages/ratchet-memory/src/ratchet/memory/retrieve.py  — 3-strategy retrieval pipeline"
echo ""
echo "Updated files:"
echo "  packages/ratchet-memory/src/ratchet/memory/module.py    — wired retrieval into on_session_start"
echo "  packages/ratchet-memory/src/ratchet/memory/__init__.py  — exports updated"
echo ""
echo "Run:"
echo "  pip install -e packages/ratchet-core -e packages/ratchet-memory --force-reinstall --no-deps"
echo "  python agents/pawl/pawl.py"
