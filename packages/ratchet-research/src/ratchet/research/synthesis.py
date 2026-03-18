"""Multi-source synthesis — summarize research findings using an LLM.

Takes search results and page content, synthesizes into a coherent
research report with citations.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any
from urllib import request as urlreq

logger = logging.getLogger("ratchet.research.synthesis")

SYNTHESIS_SYSTEM_PROMPT = """You are a research synthesizer. Given a research question and multiple source texts, create a clear, well-organized synthesis.

RULES:
1. Synthesize information across sources — don't just summarize each one separately
2. Cite sources by number [1], [2], etc.
3. Note where sources agree, disagree, or provide complementary information
4. Flag information that appears in only one source and may need verification
5. Include a confidence assessment: high (multiple corroborating sources), medium (few sources), low (single source or contradictory)
6. Structure: Key findings first, then details, then gaps/limitations
7. Be concise but thorough — aim for 300-500 words
8. If sources are insufficient to answer the question, say so explicitly

Output format:
Start with a one-line summary, then the full synthesis, then a "Sources" section listing each source number, title, and URL."""


def _call_llm(system: str, user: str, api_key: str, model: str = "claude-sonnet-4-20250514") -> str:
    payload = {
        "model": model, "max_tokens": 2048,
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
    with urlreq.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["content"][0]["text"]


@dataclass
class Source:
    """A source used in research."""
    index: int
    title: str
    url: str
    snippet: str = ""
    content: str = ""


@dataclass
class SynthesisResult:
    """Result of a research synthesis."""
    question: str = ""
    summary: str = ""
    full_text: str = ""
    sources: list[Source] = field(default_factory=list)
    confidence: str = "medium"
    error: str | None = None


def synthesize(
    question: str,
    sources: list[Source],
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> SynthesisResult:
    """
    Synthesize multiple sources into a coherent research report.

    Args:
        question: The original research question.
        sources: List of Source objects with content.
        api_key: Anthropic API key.
        model: Model for synthesis (Sonnet for quality).

    Returns:
        SynthesisResult with summary, full text, and confidence.
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    if not sources:
        return SynthesisResult(
            question=question,
            summary="No sources found.",
            full_text="No sources were found for this research question.",
            confidence="low",
        )

    # Build source text for the LLM
    source_texts = []
    for s in sources:
        text = s.content if s.content else s.snippet
        if text:
            source_texts.append(
                f"[Source {s.index}] {s.title}\nURL: {s.url}\n{text[:3000]}"
            )

    if not source_texts:
        return SynthesisResult(
            question=question,
            summary="Sources found but no content could be extracted.",
            full_text="Search returned results but page content could not be fetched.",
            sources=sources,
            confidence="low",
        )

    prompt = f"""Research question: {question}

Sources:
{'---'.join(source_texts)}

Synthesize these sources into a comprehensive answer."""

    logger.info(f"Synthesizing {len(source_texts)} sources for: {question[:60]}")

    try:
        raw = _call_llm(SYNTHESIS_SYSTEM_PROMPT, prompt, api_key, model)
    except Exception as e:
        return SynthesisResult(
            question=question, sources=sources,
            error=str(e),
        )

    # Extract summary (first line) and full text
    lines = raw.strip().split("\n", 1)
    summary = lines[0].strip()
    full_text = raw.strip()

    # Estimate confidence based on source count
    confidence = "high" if len(sources) >= 4 else "medium" if len(sources) >= 2 else "low"

    return SynthesisResult(
        question=question,
        summary=summary,
        full_text=full_text,
        sources=sources,
        confidence=confidence,
    )
