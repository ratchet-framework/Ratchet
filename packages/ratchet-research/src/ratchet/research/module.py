"""ResearchModule — deep research capability for Ratchet agents.

Wires the research pipeline into the agent lifecycle:
  - Exposes research as a callable method
  - Stores results for future retrieval
  - Publishes events when research completes
  - Reports stored research stats on heartbeat
"""

import logging
from pathlib import Path
from typing import Any, Optional

from ratchet.core.module import RatchetModule
from ratchet.research.pipeline import ResearchReport, research
from ratchet.research.store import load_research, search_research, ResearchEntry

logger = logging.getLogger("ratchet.research")


class ResearchModule(RatchetModule):
    """
    Deep research capability for Ratchet agents.

    Config keys (via context.json "research" section):
        store_dir: str — directory for research storage (default: "research")
        search_provider: str — "brave", "serper", or "duckduckgo" (auto-detect)
        planner_model: str — model for query planning (default: claude-haiku-4-5)
        synthesis_model: str — model for synthesis (default: claude-sonnet-4-20250514)
        max_queries: int — max sub-queries per research (default: 5)
        fetch_content: bool — whether to fetch page content (default: true)
    """

    name = "research"
    version = "0.1.0"

    def __init__(self) -> None:
        self.agent = None
        self._store_dir: Path | None = None
        self._search_provider: str | None = None
        self._planner_model = "claude-haiku-4-5"
        self._synthesis_model = "claude-sonnet-4-20250514"
        self._max_queries = 5
        self._fetch_content = True
        self._last_report: ResearchReport | None = None

    async def initialize(self, agent, config: dict[str, Any]) -> None:
        self.agent = agent
        store_rel = config.get("store_dir", "research")
        self._store_dir = agent.workspace / store_rel
        self._store_dir.mkdir(parents=True, exist_ok=True)

        self._search_provider = config.get("search_provider")
        self._planner_model = config.get("planner_model", "claude-haiku-4-5")
        self._synthesis_model = config.get("synthesis_model", "claude-sonnet-4-20250514")
        self._max_queries = config.get("max_queries", 5)
        self._fetch_content = config.get("fetch_content", True)

        logger.info(f"Research initialized: store={self._store_dir}")

    async def on_heartbeat(self) -> Optional[dict[str, Any]]:
        """Report research store stats."""
        stats: dict[str, Any] = {"status": "healthy"}

        entries = load_research(self._store_dir, limit=999)
        stats["total_entries"] = len(entries)

        if self._last_report:
            stats["last_research"] = {
                "question": self._last_report.question[:60],
                "sources": self._last_report.sources_found,
                "confidence": self._last_report.synthesis.confidence if self._last_report.synthesis else "unknown",
            }

        return stats

    async def on_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Handle research request events from other modules."""
        if event_type == "research.request":
            question = payload.get("question", "")
            tags = payload.get("tags", [])
            if question:
                report = await self.run_research(question, tags=tags)
                await self.agent.bus.publish("research.complete", {
                    "question": question,
                    "summary": report.synthesis.summary if report.synthesis else "",
                    "confidence": report.synthesis.confidence if report.synthesis else "unknown",
                    "sources": report.sources_found,
                })

    # --- Public API ---

    async def run_research(
        self,
        question: str,
        tags: list[str] | None = None,
        save: bool = True,
    ) -> ResearchReport:
        """
        Run a full research pipeline.

        Can be called directly from agent code or triggered via bus event.
        """
        report = research(
            question=question,
            store_dir=self._store_dir if save else None,
            search_provider=self._search_provider,
            planner_model=self._planner_model,
            synthesis_model=self._synthesis_model,
            max_queries=self._max_queries,
            fetch_content=self._fetch_content,
            save=save,
            tags=tags,
        )
        self._last_report = report

        if report.synthesis and not report.error:
            await self.agent.bus.publish("research.complete", {
                "question": question,
                "summary": report.synthesis.summary,
                "confidence": report.synthesis.confidence,
                "sources": report.sources_found,
            })

        return report

    def search_past_research(
        self, query: str, top_n: int = 5
    ) -> list[tuple[float, ResearchEntry]]:
        """Search stored research by semantic similarity."""
        return search_research(query, self._store_dir, top_n)

    def get_recent_research(self, limit: int = 10) -> list[ResearchEntry]:
        """Get recent research entries."""
        return load_research(self._store_dir, limit=limit)
