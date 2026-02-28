# Ratchet Reference Implementations

These are working implementations of Ratchet primitives from the OpenClaw reference agent (Pawl).

## Memory Primitives

**Phase 1: Extraction + LLM Retrieval**
- `bin/memory-extract` — LLM-based fact extraction from session transcripts
- `bin/memory-retrieve` — LLM-based or embedding-based fact retrieval for session start

**Phase 2: Lifecycle Management**
- `bin/memory-manage` — Decay, promotion to long-term memory, contradiction detection, purge

**Phase 3: Semantic Search**
- `bin/memory-embed` — Embed facts using OpenAI API or TF-IDF fallback
- `bin/memory-retrieve` (updated) — Cosine similarity retrieval when embeddings available

## Using these

1. Read the architecture doc: `ratchet/docs/adaptive-memory.md`
2. Adapt the scripts to your LLM provider and environment
3. Wire them into your session lifecycle: on_session_end, on_session_start, on_weekly_review
4. Test with real session transcripts

## Notes

- These scripts assume Python 3.8+
- They use `openclaw` CLI for LLM calls (or direct API if you customize)
- Facts are stored as JSONL (append-only) for portability
- No external database required
- Graceful fallback when APIs are unavailable

## License

MIT (same as Ratchet)
