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
