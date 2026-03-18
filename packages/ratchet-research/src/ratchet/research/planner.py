"""Research planner — decompose questions into sub-queries.

Takes a broad research question and uses an LLM to break it into
focused, searchable sub-queries. Each sub-query targets a specific
aspect of the question.
"""

import json
import logging
import os
from typing import Any
from urllib import request as urlreq

logger = logging.getLogger("ratchet.research.planner")

PLANNER_SYSTEM_PROMPT = """You are a research planner. Given a research question, decompose it into 3-6 focused sub-queries that together would comprehensively answer the question.

RULES:
1. Each sub-query should be a concise search query (3-8 words)
2. Sub-queries should cover different angles of the topic
3. Order them from most fundamental to most specific
4. Include at least one query for recent/current information
5. Output ONLY a JSON array of strings, no explanation

Example:
Question: "How does transformer attention work and what are the latest improvements?"
Output: ["transformer self-attention mechanism explained", "multi-head attention computation steps", "attention complexity O(n^2) problem", "flash attention efficient implementation", "2025 2026 attention mechanism improvements", "linear attention alternatives transformers"]"""


def _call_llm(system: str, user: str, api_key: str, model: str = "claude-haiku-4-5") -> str:
    payload = {
        "model": model, "max_tokens": 1024,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urlreq.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urlreq.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["content"][0]["text"]


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw.split("```json", 1)[1]
    elif raw.startswith("```"):
        raw = raw.split("```", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()


def plan_research(
    question: str,
    api_key: str | None = None,
    model: str = "claude-haiku-4-5",
    max_queries: int = 6,
) -> list[str]:
    """
    Decompose a research question into focused sub-queries.

    Args:
        question: The broad research question.
        api_key: Anthropic API key.
        model: Model for planning (Haiku is fine — this is a simple task).
        max_queries: Maximum sub-queries to generate.

    Returns:
        List of search query strings.
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    prompt = f"Research question: {question}\n\nGenerate {max_queries} focused sub-queries."
    raw = _call_llm(PLANNER_SYSTEM_PROMPT, prompt, api_key, model)
    cleaned = _clean_json(raw)

    try:
        queries = json.loads(cleaned)
        if isinstance(queries, list):
            return [str(q) for q in queries[:max_queries]]
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse planner output: {cleaned[:100]}")

    # Fallback: use the question itself
    return [question]
