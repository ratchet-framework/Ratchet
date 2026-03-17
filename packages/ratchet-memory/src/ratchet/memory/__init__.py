"""ratchet.memory — Persistent agent memory: extract, retrieve, manage, embed."""

from ratchet.memory.module import MemoryModule
from ratchet.memory.extract import ExtractionResult, extract_facts, append_facts_to_file
from ratchet.memory.retrieve import RetrievalResult, retrieve_facts, format_facts_for_injection, load_all_facts
from ratchet.memory.manage import ManageResult, Contradiction, manage_facts
from ratchet.memory.embed import EmbedResult, embed_facts, embed_tfidf, fact_text
from ratchet.memory.facts import validate_fact, credential_filter, normalize_fact, quarter_for_date
from ratchet.memory.scoring import effective_score, cosine_similarity
from ratchet.memory.providers import get_provider, AnthropicProvider, OpenAIProvider

__all__ = [
    "MemoryModule",
    "ExtractionResult", "extract_facts", "append_facts_to_file",
    "RetrievalResult", "retrieve_facts", "format_facts_for_injection", "load_all_facts",
    "ManageResult", "Contradiction", "manage_facts",
    "EmbedResult", "embed_facts", "embed_tfidf", "fact_text",
    "validate_fact", "credential_filter", "normalize_fact", "quarter_for_date",
    "effective_score", "cosine_similarity",
    "get_provider", "AnthropicProvider", "OpenAIProvider",
]
