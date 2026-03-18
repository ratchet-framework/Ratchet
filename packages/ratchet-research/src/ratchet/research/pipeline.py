"""Research pipeline — orchestrate plan → search → fetch → synthesize → store.

The main entry point for running research. Takes a question, breaks it
into sub-queries, searches, fetches page content, synthesizes, and
stores the result.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ratchet.research.planner import plan_research
from ratchet.research.search import SearchResult, search, fetch_page
from ratchet.research.store import ResearchEntry, save_research
from ratchet.research.synthesis import Source, SynthesisResult, synthesize

logger = logging.getLogger("ratchet.research.pipeline")


@dataclass
class ResearchReport:
    """Full result of a research pipeline run."""
    question: str = ""
    sub_queries: list[str] = field(default_factory=list)
    sources_found: int = 0
    sources_fetched: int = 0
    synthesis: SynthesisResult | None = None
    entry: ResearchEntry | None = None
    error: str | None = None


def research(
    question: str,
    store_dir: Path | str | None = None,
    api_key: str | None = None,
    search_provider: str | None = None,
    planner_model: str = "claude-haiku-4-5",
    synthesis_model: str = "claude-sonnet-4-20250514",
    max_queries: int = 5,
    max_results_per_query: int = 3,
    fetch_content: bool = True,
    save: bool = True,
    tags: list[str] | None = None,
) -> ResearchReport:
    """
    Run the full research pipeline.

    Flow:
      1. Plan: decompose question into sub-queries
      2. Search: run each sub-query against web search
      3. Fetch: get page content for top results (optional)
      4. Synthesize: LLM combines all sources into a report
      5. Store: persist to JSONL (optional)

    Args:
        question: The research question.
        store_dir: Directory for storing results. None = don't store.
        api_key: Anthropic API key for planning and synthesis.
        search_provider: Force search provider ("brave", "serper", "duckduckgo").
        planner_model: Model for query planning.
        synthesis_model: Model for synthesis.
        max_queries: Max sub-queries from planner.
        max_results_per_query: Max search results per sub-query.
        fetch_content: Whether to fetch full page content.
        save: Whether to save to store.
        tags: Optional tags for the stored entry.

    Returns:
        ResearchReport with all pipeline results.
    """
    report = ResearchReport(question=question)

    # Step 1: Plan
    logger.info(f"Research: {question[:80]}")
    try:
        sub_queries = plan_research(
            question, api_key=api_key, model=planner_model, max_queries=max_queries
        )
        report.sub_queries = sub_queries
        logger.info(f"Planned {len(sub_queries)} sub-queries")
    except Exception as e:
        logger.warning(f"Planner failed: {e}, using question directly")
        sub_queries = [question]
        report.sub_queries = sub_queries

    # Step 2: Search
    all_results: list[SearchResult] = []
    seen_urls: set[str] = set()

    for query in sub_queries:
        response = search(query, provider=search_provider, max_results=max_results_per_query)
        if response.error:
            logger.warning(f"Search error for '{query}': {response.error}")
            continue
        for result in response.results:
            if result.url not in seen_urls:
                all_results.append(result)
                seen_urls.add(result.url)

    report.sources_found = len(all_results)
    logger.info(f"Found {len(all_results)} unique sources")

    if not all_results:
        report.error = "No search results found"
        return report

    # Step 3: Fetch content
    sources: list[Source] = []
    for i, result in enumerate(all_results, 1):
        content = ""
        if fetch_content:
            content = fetch_page(result.url)
            if content:
                report.sources_fetched += 1

        sources.append(Source(
            index=i,
            title=result.title,
            url=result.url,
            snippet=result.snippet,
            content=content,
        ))

    logger.info(f"Fetched content from {report.sources_fetched}/{len(sources)} sources")

    # Step 4: Synthesize
    try:
        synthesis = synthesize(
            question=question,
            sources=sources,
            api_key=api_key,
            model=synthesis_model,
        )
        report.synthesis = synthesis
    except Exception as e:
        report.error = f"Synthesis failed: {e}"
        return report

    # Step 5: Store
    if save and store_dir:
        entry = ResearchEntry(
            question=question,
            summary=synthesis.summary,
            full_text=synthesis.full_text,
            sources=[{"title": s.title, "url": s.url} for s in sources],
            confidence=synthesis.confidence,
            tags=tags or [],
        )
        save_research(entry, store_dir)
        report.entry = entry

    logger.info(
        f"Research complete: {len(sources)} sources, "
        f"confidence={synthesis.confidence}"
    )
    return report
