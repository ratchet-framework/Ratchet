"""Web search interface — pluggable backends for research queries.

Supports Brave Search API and Serper (Google) with a simple
fallback to DuckDuckGo HTML scraping for zero-config usage.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any
from urllib import request as urlreq
from urllib.parse import quote_plus

logger = logging.getLogger("ratchet.research.search")


@dataclass
class SearchResult:
    """A single search result."""
    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = ""


@dataclass
class SearchResponse:
    """Response from a search query."""
    query: str = ""
    results: list[SearchResult] = field(default_factory=list)
    provider: str = ""
    error: str | None = None


def search_brave(query: str, api_key: str, max_results: int = 5) -> SearchResponse:
    """Search using Brave Search API."""
    url = f"https://api.search.brave.com/res/v1/web/search?q={quote_plus(query)}&count={max_results}"
    req = urlreq.Request(url, headers={
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    })
    try:
        with urlreq.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for item in data.get("web", {}).get("results", [])[:max_results]:
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
                source="brave",
            ))
        return SearchResponse(query=query, results=results, provider="brave")
    except Exception as e:
        return SearchResponse(query=query, provider="brave", error=str(e))


def search_serper(query: str, api_key: str, max_results: int = 5) -> SearchResponse:
    """Search using Serper (Google Search API)."""
    payload = json.dumps({"q": query, "num": max_results}).encode("utf-8")
    req = urlreq.Request(
        "https://google.serper.dev/search",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        },
        method="POST",
    )
    try:
        with urlreq.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for item in data.get("organic", [])[:max_results]:
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                source="serper",
            ))
        return SearchResponse(query=query, results=results, provider="serper")
    except Exception as e:
        return SearchResponse(query=query, provider="serper", error=str(e))


def search_duckduckgo(query: str, max_results: int = 5) -> SearchResponse:
    """Fallback search using DuckDuckGo HTML (no API key needed)."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    req = urlreq.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (ratchet-research/1.0)",
    })
    try:
        with urlreq.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        results = []
        # Parse result blocks from DDG HTML
        blocks = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL,
        )
        for href, title, snippet in blocks[:max_results]:
            # DDG wraps URLs in a redirect
            actual_url = re.search(r'uddg=([^&]+)', href)
            if actual_url:
                from urllib.parse import unquote
                href = unquote(actual_url.group(1))
            results.append(SearchResult(
                title=re.sub(r"<[^>]+>", "", title).strip(),
                url=href,
                snippet=re.sub(r"<[^>]+>", "", snippet).strip(),
                source="duckduckgo",
            ))
        return SearchResponse(query=query, results=results, provider="duckduckgo")
    except Exception as e:
        return SearchResponse(query=query, provider="duckduckgo", error=str(e))


def fetch_page(url: str, max_chars: int = 8000) -> str:
    """Fetch a web page and extract text content (rough extraction)."""
    req = urlreq.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (ratchet-research/1.0)",
    })
    try:
        with urlreq.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Strip tags, scripts, styles
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return ""


def search(
    query: str,
    provider: str | None = None,
    max_results: int = 5,
) -> SearchResponse:
    """
    Search using the best available provider.

    Auto-detects provider from environment variables:
      BRAVE_API_KEY → Brave Search
      SERPER_API_KEY → Serper (Google)
      Neither → DuckDuckGo fallback (no key needed)

    Args:
        query: Search query string.
        provider: Force a specific provider ("brave", "serper", "duckduckgo").
        max_results: Maximum results per query.

    Returns:
        SearchResponse with results.
    """
    brave_key = os.environ.get("BRAVE_API_KEY", "")
    serper_key = os.environ.get("SERPER_API_KEY", "")

    if provider == "brave" or (not provider and brave_key):
        if not brave_key:
            return SearchResponse(query=query, error="BRAVE_API_KEY not set")
        return search_brave(query, brave_key, max_results)

    if provider == "serper" or (not provider and serper_key):
        if not serper_key:
            return SearchResponse(query=query, error="SERPER_API_KEY not set")
        return search_serper(query, serper_key, max_results)

    # Fallback
    return search_duckduckgo(query, max_results)
