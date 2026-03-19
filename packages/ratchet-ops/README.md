# ratchet-ops

Business process automation for the [Ratchet framework](https://getratchet.dev).

## Install

```bash
pip install ratchet-ops
```

## What it does

- **Invoicing** — Parse invoices from text with rule-based extraction, duplicate detection, and status tracking
- **Expenses** — Track spending by category and vendor, with period summaries and recurring expense support
- **Cost routing** — Route LLM tasks to the cheapest capable model (Haiku/Sonnet/Opus), log costs, project budgets

```python
from ratchet.ops import OpsModule

agent.register(OpsModule())

# Or use components directly
from ratchet.ops import select_model, calculate_cost

model = select_model("extract facts from this transcript")  # → claude-haiku-4-5
cost = calculate_cost(model, input_tokens=5000, output_tokens=500)
```

## License

MIT
