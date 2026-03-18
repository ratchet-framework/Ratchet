"""ratchet.research — Deep research with web search, synthesis, and vector storage."""

from ratchet.research.module import ResearchModule
from ratchet.research.pipeline import ResearchReport, research
from ratchet.research.planner import plan_research
from ratchet.research.search import SearchResult, SearchResponse, search, fetch_page
from ratchet.research.synthesis import SynthesisResult, Source, synthesize
from ratchet.research.store import ResearchEntry, save_research, load_research, search_research

__all__ = [
    "ResearchModule",
    "ResearchReport", "research",
    "plan_research",
    "SearchResult", "SearchResponse", "search", "fetch_page",
    "SynthesisResult", "Source", "synthesize",
    "ResearchEntry", "save_research", "load_research", "search_research",
]
