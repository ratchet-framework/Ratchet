# Epic 4: Embedding Quality

**Status:** Design complete  
**Author:** Claude Opus (2026-03-01)  
**Priority:** High — blocks reliable semantic retrieval (Phase 3+4)

---

## Problem Statement

The workspace was indexed using TF-IDF (128-dim bag-of-words) because the OpenAI API key wasn't configured in the server environment at build time. TF-IDF on documents of wildly varying length produces unreliable similarity scores — a 50-word fact and a 4000-char document get projected into the same 128-dim space via hash bucketing, making cosine similarity nearly meaningless.

Additionally, the engineering review identified a critical incompatibility: TF-IDF embeddings (128-dim) and OpenAI embeddings (1536-dim) cannot be compared. If some facts were embedded with TF-IDF and others with OpenAI, cosine similarity will crash or return nonsense. There's no dimension compatibility check.

Second problem: the extraction LLM assigns importance scores (0.0–1.0) without calibration. As models change or prompt behavior drifts, scores become inconsistent across time.

---

## 1. OpenAI Key Status

**Available.** `OPENAI_API_KEY` is set in the environment (prefix: `sk-proj-dZ...`).

The existing code in `memory-embed` and `workspace-index` already supports OpenAI `text-embedding-3-small` as the primary path with TF-IDF fallback. The key just wasn't present when the initial indexing ran.

### Re-embedding path

```bash
# Re-embed all facts (51 facts)
python3 workspace/bin/memory-embed --all

# Re-index all documents (79 documents)
python3 workspace/bin/workspace-index --rebuild
```

**Time estimate:** ~5 seconds total. Both scripts batch API calls (100 items per batch for facts, 50 for documents). At 130 total items, this is 2 API calls.

**Cost estimate:**

| Item | Count | Avg tokens/item | Total tokens | Cost @ $0.02/1M tokens |
|------|-------|-----------------|-------------|----------------------|
| Facts | 51 | ~60 | ~3,060 | $0.0001 |
| Documents | 79 | ~800 | ~63,200 | $0.0013 |
| **Total** | **130** | — | **~66,260** | **$0.0014** |

Cost is negligible. Even at 500 documents + 500 facts, total re-embedding costs ~$0.02.

---

## 2. Embedding Model Selection

### Recommendation: `text-embedding-3-small` (1536 dimensions)

| Model | Dimensions | MTEB Score | Cost/1M tokens | Verdict |
|-------|-----------|------------|-----------------|---------|
| text-embedding-3-small | 1536 | 62.3% | $0.02 | **Use this** |
| text-embedding-3-large | 3072 | 64.6% | $0.13 | Overkill for <1000 items |
| text-embedding-ada-002 | 1536 | 61.0% | $0.10 | Legacy, worse and 5× more expensive |

**Rationale:**
- At 50–500 facts and 100–500 documents, the quality gap between small and large is imperceptible. Both dramatically outperform TF-IDF for semantic similarity.
- 1536 dimensions is fine for brute-force cosine similarity on <1000 items. No ANN index needed.
- Cost difference is 6.5× between small and large — irrelevant at this scale, but no reason to pay more for no benefit.
- The existing code already uses `text-embedding-3-small`. No changes needed.

### Dimension compatibility fix (required)

Add a check when loading embeddings: if stored embedding dimensions don't match the current model's output dimensions (1536), flag for re-embedding. This prevents the TF-IDF/OpenAI incompatibility the engineering review identified.

```python
# In memory-retrieve and pattern-detect, before cosine_similarity:
def validate_embedding_dims(embeddings_dict, expected_dim=1536):
    """Flag embeddings with wrong dimensions for re-embedding."""
    mismatched = {k for k, v in embeddings_dict.items() if len(v) != expected_dim}
    if mismatched:
        print(f"  [warn] {len(mismatched)} embeddings have wrong dimensions, need re-embedding", file=sys.stderr)
    return mismatched
```

---

## 3. Incremental Re-embedding Strategy

### Current behavior (already correct for facts)

`memory-embed` already checks `existing` embeddings dict and only embeds facts not yet present. This is the right behavior for new facts.

### What's missing

| Scenario | Current behavior | Correct behavior |
|----------|-----------------|-----------------|
| New fact added | ✅ Embeds only new fact | — |
| Fact content updated | ❌ Skips (ID already in embeddings) | Re-embed |
| Model changed | ❌ No detection | Re-embed all |
| TF-IDF → OpenAI migration | ❌ No detection | Re-embed all |

### Design: content-hash tracking

Add a `content_hash` field to the embeddings metadata. When embedding, hash the fact text. On subsequent runs, compare hashes — if content changed, re-embed.

```python
# embeddings.json structure change:
{
    "metadata": {
        "model": "text-embedding-3-small",
        "dimensions": 1536,
        "last_full_rebuild": "2026-03-01T00:00:00Z"
    },
    "vectors": {
        "fact-id-1": {
            "embedding": [0.1, 0.2, ...],
            "content_hash": "a1b2c3...",
            "embedded_at": "2026-03-01T00:00:00Z"
        }
    }
}
```

**Triggers for re-embedding:**
- **New fact:** Automatic on next `memory-embed` run (already works)
- **Updated fact:** Detected via content hash mismatch → re-embed that fact
- **Model change:** Detected via `metadata.model` mismatch → `--rebuild` flag
- **Weekly refresh:** Not needed. Embeddings are deterministic — same input = same output. Only re-embed on content change.

### Implementation changes to `memory-embed`

1. Store `metadata` block with model name and dimensions
2. Store `content_hash` per fact alongside embedding
3. On load, check `metadata.model` — if different, force full rebuild
4. On each fact, check `content_hash` — if different, re-embed

For `workspace-index`: already uses `file_hash` for change detection. ✅ No changes needed.

---

## 4. Importance Score Calibration

### Problem

The extraction LLM assigns importance 0.0–1.0 at extraction time. This score is subjective and model-dependent. If the model changes (Claude 3.5 → Claude 4), or if prompt behavior drifts, a fact scored 0.8 six months ago might be scored 0.5 today on the same content.

The engineering review also found double-decay: `memory-manage` decays stored importance, and `memory-retrieve` applies a second recency decay at query time. This makes calibration even more important — if base scores drift, the compounding effect is amplified.

### Design: weekly calibration check

**Script:** `bin/importance-calibrate`  
**Schedule:** Weekly (Friday review cron, before `memory-manage`)  
**Cost:** ~$0.003 per run (10 facts × ~200 tokens each, using Claude Haiku)

#### Algorithm

```
1. Load all active facts from facts-*.jsonl
2. Sample 10 random facts (stratified: 3 high importance ≥0.7, 4 medium 0.4-0.7, 3 low <0.4)
3. For each fact, ask the extraction LLM to re-score importance (same prompt template as memory-extract)
4. Compare re-scored values to stored values
5. Compute average absolute drift = mean(|stored - rescored|) across 10 facts
6. If drift > 0.15: flag for manual review
7. Log results to memory/calibration-log.jsonl
```

#### Calibration prompt

```
You are scoring the importance of a memory fact for a personal AI assistant.
Score from 0.0 (trivial) to 1.0 (critical).

Categories and baselines:
- incident/decision: ~0.9
- vehicle/maintenance: ~0.8
- preference/process: ~0.6
- casual/operational: ~0.3

Fact: "{content}"
Category: {category}
Tags: {tags}

Return ONLY a JSON object: {"importance": <float>}
```

#### Drift response

| Drift level | Action |
|------------|--------|
| ≤ 0.10 | No action. Log and continue. |
| 0.10–0.15 | Log warning. No action yet. |
| > 0.15 | Flag for manual review. Write alert to `memory/calibration-alerts.md`. Do NOT auto-correct scores. |
| > 0.25 | Flag as critical. Scores may need full re-calibration. |

**Why not auto-correct:** The new scores might be wrong too. If the model drifted, auto-correcting overwrites historical assessments with the new model's bias. Better to flag and let a human decide whether to re-score all facts, adjust the prompt, or accept the drift.

#### Output format (calibration-log.jsonl)

```json
{
    "timestamp": "2026-03-07T04:00:00Z",
    "sample_size": 10,
    "avg_drift": 0.08,
    "max_drift": 0.15,
    "drift_alert": false,
    "samples": [
        {"id": "abc123", "stored": 0.8, "rescored": 0.75, "drift": 0.05},
        ...
    ]
}
```

---

## 5. Embedding Quality Evaluation (Smoke Test)

### Design: known-answer retrieval test

After any re-embedding, run a smoke test with known queries and expected results.

**Script:** `bin/embedding-smoke-test`

#### Test cases

```python
SMOKE_TESTS = [
    {
        "query": "Tacoma maintenance",
        "must_match_any": ["tacoma", "brakes", "oil change", "maintenance"],
        "description": "Vehicle maintenance facts should surface for Tacoma queries"
    },
    {
        "query": "Welsh Terrier",
        "must_match_any": ["towyn", "denbigh", "welsh terrier", "dog"],
        "description": "Pet-related facts should surface"
    },
    {
        "query": "incident process",
        "must_match_any": ["inc-", "incident", "prevention", "root cause"],
        "description": "Incident-related documents should surface"
    },
    {
        "query": "racing autocross",
        "must_match_any": ["wrx", "scca", "autocross", "racing", "47"],
        "description": "Motorsports facts should surface"
    }
]
```

#### Algorithm

```
For each test case:
  1. Embed the query using text-embedding-3-small
  2. Compute cosine similarity against all fact embeddings
  3. Take top 5 results
  4. Check if any of must_match_any keywords appear in top 3 results' content
  5. PASS if at least 1 keyword match in top 3, FAIL otherwise

Overall: PASS if all test cases pass. FAIL if any fails.
```

#### Integration

- Run automatically after `memory-embed --all` or `workspace-index --rebuild`
- Run manually: `python3 workspace/bin/embedding-smoke-test`
- Exit code 0 = all pass, exit code 1 = failures (for CI/cron integration)

---

## 6. Cost and Maintenance Summary

### One-time re-embedding cost

| Action | Cost |
|--------|------|
| Re-embed 51 facts | $0.0001 |
| Re-index 79 documents | $0.0013 |
| **Total** | **~$0.002** |

### Ongoing costs

| Trigger | Frequency | Est. cost/run |
|---------|-----------|---------------|
| New facts (incremental) | Per session (~5 facts) | $0.000006 |
| Updated facts | Rare | $0.000002 |
| Importance calibration | Weekly | $0.003 |
| Smoke test | After re-embedding | $0.0001 |
| Full re-index (documents) | When files change | $0.001 |

**Monthly estimate:** < $0.02/month at current scale. At 500 facts + 500 documents: < $0.10/month.

Embedding costs are irrelevant to the budget. The real cost is LLM calls for extraction and calibration, which are also negligible.

### Re-embedding triggers

| Trigger | Scope | When |
|---------|-------|------|
| New fact extracted | Single fact | After `memory-extract` |
| Fact content updated | Single fact | On content hash change |
| Embedding model upgrade | All facts + documents | Manual decision |
| TF-IDF → OpenAI migration | All facts + documents | One-time (now) |
| Weekly maintenance | None (no refresh needed) | — |

**Key insight:** Embeddings are deterministic. Same text + same model = same embedding. There is no reason to periodically re-embed unchanged content. Only embed on content change or model change.

---

## Implementation Plan

### Phase 1: Immediate (unblocks Phase 3 retrieval)

1. Run `python3 workspace/bin/memory-embed --all` to re-embed facts with OpenAI
2. Run `python3 workspace/bin/workspace-index --rebuild` to re-index documents
3. Run smoke test to validate

### Phase 2: Robustness (1-2 sessions)

4. Add content-hash tracking to `memory-embed` for incremental updates
5. Add dimension compatibility check to `memory-retrieve` and `pattern-detect`
6. Fix the double-decay bug (engineering review finding)

### Phase 3: Calibration (1 session)

7. Build `bin/importance-calibrate` script
8. Add to Friday review cron (before `memory-manage`)
9. Build `bin/embedding-smoke-test`

### Phase 4: Monitoring

10. Add embedding method + dimension to memory pipeline health output
11. Track calibration drift over time in `calibration-log.jsonl`

---

## Dependencies

- **OpenAI API key:** ✅ Available
- **Existing code:** `memory-embed` and `workspace-index` already support OpenAI path — no code changes needed for Phase 1
- **Double-decay fix:** Separate from this epic but related — tracked in engineering review findings

---

## Success Criteria

- [ ] All facts embedded with `text-embedding-3-small` (1536-dim, no TF-IDF)
- [ ] All workspace documents indexed with OpenAI embeddings
- [ ] Smoke test passes (4/4 known queries return relevant results in top 3)
- [ ] Incremental embedding works (new fact → embedded on next run, no full rebuild)
- [ ] Weekly calibration check runs without errors
- [ ] No mixed-dimension embeddings in storage
