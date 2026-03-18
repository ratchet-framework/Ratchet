# ratchet-research

Deep research capability for the [Ratchet framework](https://getratchet.dev).

## Install

```bash
pip install ratchet-research
```

## What it does

Give your agent a research question. It decomposes it into sub-queries, searches the web, fetches page content, synthesizes everything into a cited report, and stores the result for future retrieval.

```python
from ratchet.research import ResearchModule

# Register with your agent
agent.register(ResearchModule())

# Or use the pipeline directly
from ratchet.research import research
report = research("What are the latest improvements to transformer attention mechanisms?")
print(report.synthesis.summary)
```

## Pipeline

1. **Plan** — LLM decomposes question into 3-6 focused sub-queries
2. **Search** — Web search via Brave, Serper, or DuckDuckGo (auto-detect)
3. **Fetch** — Extract text content from result pages
4. **Synthesize** — LLM combines sources into a cited report with confidence rating
5. **Store** — Persist to JSONL with TF-IDF vector search for retrieval

## Search providers

Set one of these environment variables to use a paid search API:

- `BRAVE_API_KEY` — Brave Search (recommended)
- `SERPER_API_KEY` — Serper (Google results)

No key? Falls back to DuckDuckGo HTML scraping automatically.

## License

MIT
