"""Templates for scaffolding agents and modules.

Plain Python string templates — no Jinja dependency needed.
"""

CONTEXT_JSON = """\
{{
  "name": "{agent_name}",
  "timezone": "{timezone}",
  "units": "imperial",
  "locale": "en-US",
  "heartbeat_interval_minutes": 30,
  "quiet_hours": {{
    "start": "23:00",
    "end": "07:00"
  }},
  "memory": {{
    "facts_dir": "memory/facts",
    "provider": "anthropic",
    "max_retrieval": 15
  }},
  "pilot": {{
    "incidents_dir": "incidents",
    "trust_path": "config/trust.json",
    "guardrails_path": "config/guardrails.json"
  }}
}}
"""

AGENT_PY = """\
\"\"\"
{agent_name} — a Ratchet agent.

Usage:
    python {filename}
\"\"\"

import asyncio
import logging

from ratchet.core import Agent
from ratchet.memory import MemoryModule
from ratchet.pilot import PilotModule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    agent = Agent(name="{agent_name}", config_path="config/context.json")
    agent.register(MemoryModule())
    agent.register(PilotModule())

    await agent.start()
    print(f"\\n✅ Agent '{{agent.name}}' started with {{len(agent.modules)}} module(s):")
    for mod in agent.modules:
        print(f"   {{mod}}")

    report = await agent.heartbeat()
    print(f"\\n💓 Heartbeat report:")
    for name, status in report.items():
        print(f"   {{name}}: {{status}}")

    await agent.stop()
    print(f"\\n🔩 Agent stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
"""

TRUST_JSON = """\
{{
  "schema": "ratchet-trust-v1",
  "currentTier": 1,
  "updatedAt": "{today}",
  "tiers": {{
    "1": {{
      "label": "Read & Respond",
      "description": "Read files, search, answer questions. No external actions.",
      "status": "unlocked",
      "unlockedAt": "{today}"
    }},
    "2": {{
      "label": "Schedule & Organize",
      "description": "Create cron jobs, write files, commit to GitHub, manage workspace.",
      "status": "locked",
      "criteria": {{
        "weeksCleanRequired": 2,
        "p1IncidentsAllowed": 0,
        "aaronConfirmation": false
      }}
    }},
    "3": {{
      "label": "External Comms",
      "description": "Send email, post publicly, communicate externally.",
      "status": "locked",
      "criteria": {{
        "weeksCleanRequired": 4,
        "p1IncidentsAllowed": 0,
        "aaronConfirmation": false
      }}
    }}
  }},
  "regressionRules": {{
    "p1ExternalImpact": {{
      "action": "drop",
      "tiers": 1,
      "recovery": "full-requalification"
    }},
    "p1NoExternalImpact": {{
      "action": "freeze",
      "weeks": 2,
      "recovery": "prevention-plus-clean"
    }},
    "p2SameClass2in4weeks": {{
      "action": "freeze",
      "weeks": 2,
      "recovery": "prevention-plus-clean"
    }},
    "p2Any3in4weeks": {{
      "action": "drop",
      "tiers": 1,
      "recovery": "full-requalification"
    }},
    "patternSystemic": {{
      "action": "aaron-review",
      "recovery": "aaron-decides"
    }}
  }},
  "regressionHistory": [],
  "advancementHistory": [
    {{
      "from": 0,
      "to": 1,
      "date": "{today}",
      "note": "Baseline — agent created"
    }}
  ]
}}
"""

GUARDRAILS_JSON = """\
[
  {{
    "id": "GR-001",
    "source": "default",
    "pattern": "commit_to_public_repo",
    "keywords": ["git push", "git commit", "public repo", "commit"],
    "trigger": "pushing to a public repository",
    "rule": "Verify no private files in staging area. Check pre-commit hooks.",
    "severity": "hard",
    "fire_count": 0
  }},
  {{
    "id": "GR-002",
    "source": "default",
    "pattern": "external_communication",
    "keywords": ["send email", "post publicly", "tweet", "slack message"],
    "trigger": "sending any external communication",
    "rule": "Verify trust tier allows external comms. Queue for approval if not T3+.",
    "severity": "hard",
    "fire_count": 0
  }},
  {{
    "id": "GR-003",
    "source": "default",
    "pattern": "timezone_action",
    "keywords": ["cron", "schedule", "timezone", "reminder", "briefing"],
    "trigger": "creating time-based automation",
    "rule": "Verify current timezone from context.json before creating time-sensitive tasks.",
    "severity": "soft",
    "fire_count": 0
  }}
]
"""

BACKLOG_MD = """\
# Backlog

| ID | Priority | Description | Status | Created |
|----|----------|-------------|--------|---------|
| BL-001 | P2 | Set up first incident postmortem template | Open | {today} |
| BL-002 | P3 | Configure communication channel (Telegram/Discord) | Open | {today} |
"""

NORTH_STAR_MD = """\
# North Star

**{agent_name} becomes an agent that requires less from you each week while doing more right.**

---

## What success looks like

You check in once a day. The briefing is already there. Issues were caught and fixed
while you were away. The backlog is being worked. You didn't have to ask for any of it.

---

## Operating rhythm

| Cadence | What happens |
|---------|-------------|
| **Continuous** | Agent executes against backlog via heartbeat |
| **Weekly** | Friday review: metrics, trust tier check, memory synthesis |
| **Monthly** | Milestone check: are we on track? |

---

*Created: {today}*
"""

INCIDENT_README = """\
# Incidents

When something goes wrong, log it here as `INC-NNN-short-description.md`.

Each incident should include:
- **Date** and **Severity** (P1/P2/P3)
- **Root cause** — why it happened
- **Blast radius** — what else might be affected
- **Prevention tasks** — checklist of fixes (these go into the backlog)

Example: `INC-001-timezone-mismatch.md`

The incident loop is the ratchet mechanism — every fix locks in and prevents regression.
"""

GITIGNORE = """\
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.env
memory/facts/
memory/*.jsonl
memory/embeddings.json
pending-actions.json
metrics.json
"""

README_MD = """\
# {agent_name}

A [Ratchet](https://getratchet.dev) agent.

## Quick start

```bash
pip install ratchet-core ratchet-memory ratchet-pilot
python {filename}
```

## Structure

```
{agent_slug}/
├── {filename}           # Agent entry point
├── config/
│   ├── context.json     # Agent configuration
│   ├── trust.json       # Trust tier state
│   └── guardrails.json  # Preflight rules
├── incidents/           # Postmortems (INC-*.md)
├── memory/              # Facts, embeddings, logs
├── BACKLOG.md           # Self-directed work queue
└── NORTH-STAR.md        # Mission and goals
```

## License

MIT
"""

# --- Module templates ---

MODULE_INIT_PY = """\
\"\"\"{module_description}\"\"\"

from {import_path}.module import {class_name}

__all__ = ["{class_name}"]
"""

MODULE_PY = """\
\"\"\"
{class_name} — {module_description}
\"\"\"

import logging
from typing import Any, Optional

from ratchet.core.module import RatchetModule

logger = logging.getLogger("ratchet.{module_name}")


class {class_name}(RatchetModule):
    \"\"\"{module_description}\"\"\"

    name = "{module_name}"
    version = "0.1.0"

    def __init__(self) -> None:
        self.agent = None

    async def initialize(self, agent, config: dict[str, Any]) -> None:
        self.agent = agent
        logger.info(f"{class_name} initialized")

    async def on_session_start(self, context: dict[str, Any]) -> None:
        pass

    async def on_session_end(self, context: dict[str, Any]) -> None:
        pass

    async def on_heartbeat(self) -> Optional[dict[str, Any]]:
        return {{"status": "healthy"}}

    async def shutdown(self) -> None:
        pass
"""

MODULE_PYPROJECT = """\
[project]
name = "ratchet-{module_name}"
version = "0.1.0"
description = "{module_description}"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
dependencies = [
    "ratchet-core>=0.1.0",
]

[project.urls]
Homepage = "https://getratchet.dev"
Repository = "https://github.com/ratchet-framework/Ratchet"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ratchet"]

[tool.hatch.build.targets.editable]
packages = ["src/ratchet"]
"""

MODULE_README = """\
# ratchet-{module_name}

{module_description}

Part of the [Ratchet framework](https://getratchet.dev).

## Install

```bash
pip install ratchet-{module_name}
```

## License

MIT
"""

MODULE_NAMESPACE_INIT = """\
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
"""
