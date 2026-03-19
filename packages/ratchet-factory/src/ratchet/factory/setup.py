"""Platform adapter setup — wire Ratchet into existing agent runtimes.

Currently supported:
  - OpenClaw: detects workspace at /root/.openclaw/workspace,
    creates config files, installs bin/ wrappers.
"""

import json
import logging
import os
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("ratchet.factory.setup")


def _today() -> str:
    return datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d")


def _write(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


# --- OpenClaw Wrapper Scripts ---

WRAPPER_MEMORY_EXTRACT = '''#!/usr/bin/env python3
"""Ratchet wrapper — memory-extract via ratchet.memory package."""
import sys, os, argparse
from datetime import datetime, timezone, timedelta
from ratchet.memory import extract_facts, append_facts_to_file, get_provider, quarter_for_date

WORKSPACE = os.environ.get("RATCHET_WORKSPACE", "/root/.openclaw/workspace")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")

def et_today():
    return datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d")

parser = argparse.ArgumentParser()
parser.add_argument("--session", default=None)
parser.add_argument("--transcript", default=None)
args = parser.parse_args()

session_date = args.session or et_today()
quarter = quarter_for_date(session_date)

if args.transcript:
    with open(args.transcript) as f:
        transcript = f.read()
elif not sys.stdin.isatty():
    transcript = sys.stdin.read()
else:
    path = os.path.join(MEMORY_DIR, f"{session_date}.md")
    if not os.path.exists(path):
        print(f"ERROR: Transcript not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        transcript = f.read()

if not transcript.strip():
    print("ERROR: Empty transcript", file=sys.stderr)
    sys.exit(1)

provider = get_provider("anthropic")
result = extract_facts(transcript, session_date, provider, MEMORY_DIR)

if result.facts:
    outfile = append_facts_to_file(result.facts, quarter, MEMORY_DIR)
    print(f"Extracted: {result.count} facts")
    print(f"Written to: {outfile}")
    for f in result.facts:
        print(f"  [{f.get('category','?')}] ({f.get('importance',0):.1f}) {f['content'][:100]}")
else:
    print(f"Extracted: 0 facts")
print(f"Rejected (validation): {result.rejected_validation}")
print(f"Rejected (credentials): {result.rejected_credentials}")
'''

WRAPPER_MEMORY_RETRIEVE = '''#!/usr/bin/env python3
"""Ratchet wrapper — memory-retrieve via ratchet.memory package."""
import argparse, os
from ratchet.memory import retrieve_facts, format_facts_for_injection, get_provider

WORKSPACE = os.environ.get("RATCHET_WORKSPACE", "/root/.openclaw/workspace")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")

parser = argparse.ArgumentParser()
parser.add_argument("--context", default=None)
parser.add_argument("--top", type=int, default=15)
parser.add_argument("--force-llm", action="store_true")
parser.add_argument("--force-embeddings", action="store_true")
args = parser.parse_args()

strategy = None
if args.force_llm: strategy = "llm"
elif args.force_embeddings: strategy = "embedding"

provider = get_provider("anthropic")
result = retrieve_facts(memory_dir=MEMORY_DIR, context=args.context,
    top_n=args.top, provider=provider, force_strategy=strategy)
print(format_facts_for_injection(result.facts))
'''

WRAPPER_MEMORY_MANAGE = '''#!/usr/bin/env python3
"""Ratchet wrapper — memory-manage via ratchet.memory package."""
import sys, os
from ratchet.memory.manage import manage_facts

WORKSPACE = os.environ.get("RATCHET_WORKSPACE", "/root/.openclaw/workspace")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
dry_run = "--dry-run" in sys.argv or "--report-only" in sys.argv

result = manage_facts(memory_dir=MEMORY_DIR, dry_run=dry_run)
print(f"Total: {result.total_facts} | Tiers: {result.tier_counts}")
print(f"Promoted: {len(result.promoted)} | Contradictions: {len(result.contradictions)} | Purged: {len(result.purged)}")
if dry_run: print("(DRY RUN)")
'''

WRAPPER_MEMORY_EMBED = '''#!/usr/bin/env python3
"""Ratchet wrapper — memory-embed via ratchet.memory package."""
import sys, os
from ratchet.memory.embed import embed_facts

WORKSPACE = os.environ.get("RATCHET_WORKSPACE", "/root/.openclaw/workspace")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
dry_run = "--dry-run" in sys.argv
fact_id = None
for i, arg in enumerate(sys.argv):
    if arg == "--fact-id" and i + 1 < len(sys.argv):
        fact_id = sys.argv[i + 1]

result = embed_facts(memory_dir=MEMORY_DIR, fact_id=fact_id, dry_run=dry_run)
print(f"Method: {result.method} | Embedded: {result.embedded_count} | Already: {result.already_embedded}")
'''

WRAPPER_TRUST_CHECK = '''#!/usr/bin/env python3
"""Ratchet wrapper — trust-check via ratchet.pilot package."""
import json, sys, os
from ratchet.pilot import parse_all_incidents, check_trust

WORKSPACE = os.environ.get("RATCHET_WORKSPACE", "/root/.openclaw/workspace")
INCIDENTS_DIR = os.path.join(WORKSPACE, "incidents")
TRUST_PATH = os.path.join(WORKSPACE, "trust.json")

if not os.path.exists(TRUST_PATH):
    TRUST_PATH = os.path.join(WORKSPACE, "config", "trust.json")

do_summary = "--summary" in sys.argv
do_apply = "--apply" in sys.argv

incidents = parse_all_incidents(INCIDENTS_DIR)
result = check_trust(incidents, TRUST_PATH, apply=do_apply)

if do_summary:
    print(f"Trust Check — {result.checked_at}")
    print(f"  Tier: T{result.current_tier}")
    print(f"  Last 4 weeks: P1={result.incident_counts['p1_last_4_weeks']} P2={result.incident_counts['p2_last_4_weeks']} P3={result.incident_counts['p3_last_4_weeks']}")
    for name, t in result.triggers.items():
        print(f"  {name}: {'TRIGGERED' if t.triggered else 'clear'}")
    print(f"  Regression: {'YES' if result.regression.required else 'No'}")
else:
    print(json.dumps({"checkedAt": result.checked_at, "currentTier": result.current_tier,
        "regression": {"required": result.regression.required, "action": result.regression.action}}, indent=2))
if result.regression.required: sys.exit(2)
'''

WRAPPER_PREFLIGHT_CHECK = '''#!/usr/bin/env python3
"""Ratchet wrapper — preflight-check via ratchet.pilot package."""
import json, sys, argparse, os
from ratchet.pilot import preflight_check

WORKSPACE = os.environ.get("RATCHET_WORKSPACE", "/root/.openclaw/workspace")
GUARDRAILS_PATH = os.path.join(WORKSPACE, "guardrails.json")
if not os.path.exists(GUARDRAILS_PATH):
    GUARDRAILS_PATH = os.path.join(WORKSPACE, "config", "guardrails.json")

parser = argparse.ArgumentParser()
parser.add_argument("text", nargs="?")
parser.add_argument("--text", dest="text_flag")
parser.add_argument("--update-counts", action="store_true")
args = parser.parse_args()

action_text = args.text or args.text_flag
if not action_text and not sys.stdin.isatty():
    action_text = sys.stdin.read().strip()
if not action_text:
    print(json.dumps({"error": "No action description provided."}))
    sys.exit(1)

result = preflight_check(action_text, GUARDRAILS_PATH, update_counts=args.update_counts)
print(json.dumps({"action": result.action, "overall_severity": result.overall_severity,
    "match_count": len(result.matches), "verdict": result.verdict}, indent=2))
sys.exit({"clear": 0, "soft": 1, "hard": 2}[result.overall_severity])
'''

WRAPPER_RESEARCH = '''#!/usr/bin/env python3
"""Ratchet wrapper — deep research via ratchet.research package."""
import argparse, os
from ratchet.research import research

WORKSPACE = os.environ.get("RATCHET_WORKSPACE", "/root/.openclaw/workspace")
STORE_DIR = os.path.join(WORKSPACE, "research")

parser = argparse.ArgumentParser(description="Deep research")
parser.add_argument("question", help="Research question")
parser.add_argument("--no-save", action="store_true")
parser.add_argument("--no-fetch", action="store_true")
parser.add_argument("--tags", nargs="*", default=[])
args = parser.parse_args()

report = research(question=args.question, store_dir=None if args.no_save else STORE_DIR,
    fetch_content=not args.no_fetch, save=not args.no_save, tags=args.tags)

print(f"Sub-queries: {len(report.sub_queries)}")
for q in report.sub_queries:
    print(f"  - {q}")
print(f"Sources: {report.sources_found} found, {report.sources_fetched} fetched")
if report.synthesis:
    print(f"Confidence: {report.synthesis.confidence}")
    print(f"\\n{report.synthesis.full_text}")
elif report.error:
    print(f"Error: {report.error}")
'''

WRAPPER_COST_REPORT = '''#!/usr/bin/env python3
"""Ratchet wrapper — cost report via ratchet.ops package."""
import argparse, os
from ratchet.ops import summarize_costs, summarize_spending

WORKSPACE = os.environ.get("RATCHET_WORKSPACE", "/root/.openclaw/workspace")
OPS_DIR = os.path.join(WORKSPACE, "ops")

parser = argparse.ArgumentParser()
parser.add_argument("--period", default="month", choices=["day", "week", "month"])
args = parser.parse_args()

costs = summarize_costs(OPS_DIR, period=args.period)
print(f"API Costs ({args.period}):")
print(f"  Total: ${costs.total_cost:.4f} ({costs.total_calls} calls)")
if costs.by_model:
    for model, cost in costs.by_model.items():
        print(f"  {model}: ${cost:.4f}")

spending = summarize_spending(OPS_DIR, period=args.period)
if spending.total > 0:
    print(f"\\nExpenses ({args.period}):")
    print(f"  Total: ${spending.total:.2f}")
    for cat, amt in spending.by_category.items():
        print(f"  {cat}: ${amt:.2f}")
'''

# Wrappers registry
WRAPPERS = {
    "memory-extract": WRAPPER_MEMORY_EXTRACT,
    "memory-retrieve": WRAPPER_MEMORY_RETRIEVE,
    "memory-manage": WRAPPER_MEMORY_MANAGE,
    "memory-embed": WRAPPER_MEMORY_EMBED,
    "trust-check": WRAPPER_TRUST_CHECK,
    "preflight-check": WRAPPER_PREFLIGHT_CHECK,
    "research": WRAPPER_RESEARCH,
    "cost-report": WRAPPER_COST_REPORT,
}

# Config templates
TRUST_JSON_TEMPLATE = {
    "schema": "ratchet-trust-v1",
    "currentTier": 1,
    "tiers": {
        "1": {"label": "Read & Respond", "status": "unlocked"},
        "2": {"label": "Schedule & Organize", "status": "locked",
              "criteria": {"weeksCleanRequired": 2, "p1IncidentsAllowed": 0, "aaronConfirmation": False}},
        "3": {"label": "External Comms", "status": "locked",
              "criteria": {"weeksCleanRequired": 4, "p1IncidentsAllowed": 0, "aaronConfirmation": False}},
    },
    "regressionRules": {
        "p1ExternalImpact": {"action": "drop", "tiers": 1, "recovery": "full-requalification"},
        "p1NoExternalImpact": {"action": "freeze", "weeks": 2, "recovery": "prevention-plus-clean"},
        "p2SameClass2in4weeks": {"action": "freeze", "weeks": 2, "recovery": "prevention-plus-clean"},
        "p2Any3in4weeks": {"action": "drop", "tiers": 1, "recovery": "full-requalification"},
        "patternSystemic": {"action": "aaron-review", "recovery": "aaron-decides"},
    },
    "regressionHistory": [],
    "advancementHistory": [],
}

GUARDRAILS_TEMPLATE = [
    {"id": "GR-001", "source": "default", "pattern": "commit_to_public_repo",
     "keywords": ["git push", "git commit", "public repo", "commit"],
     "trigger": "pushing to a public repository",
     "rule": "Verify no private files in staging area.",
     "severity": "hard", "fire_count": 0},
    {"id": "GR-002", "source": "default", "pattern": "external_communication",
     "keywords": ["send email", "post publicly", "tweet", "slack message"],
     "trigger": "sending any external communication",
     "rule": "Verify trust tier allows external comms.",
     "severity": "hard", "fire_count": 0},
    {"id": "GR-003", "source": "default", "pattern": "timezone_action",
     "keywords": ["cron", "schedule", "timezone", "reminder", "briefing"],
     "trigger": "creating time-based automation",
     "rule": "Verify current timezone from context.json.",
     "severity": "soft", "fire_count": 0},
]


def setup_openclaw(
    workspace: Path | str | None = None,
    skip_existing: bool = True,
    install_wrappers: bool = True,
) -> dict[str, Any]:
    """
    Set up Ratchet in an existing OpenClaw workspace.

    Detects the workspace, creates config files, installs bin/ wrappers.

    Args:
        workspace: Override workspace path. Auto-detects if None.
        skip_existing: Don't overwrite existing config files.
        install_wrappers: Install bin/ wrapper scripts.

    Returns:
        Dict with setup results: created files, skipped files, wrapper count.
    """
    # Auto-detect workspace
    if workspace is None:
        candidates = [
            Path("/root/.openclaw/workspace"),
            Path.home() / ".openclaw" / "workspace",
        ]
        workspace = next((p for p in candidates if p.exists()), None)
        if workspace is None:
            raise FileNotFoundError(
                "Could not find OpenClaw workspace. "
                "Expected at /root/.openclaw/workspace or ~/.openclaw/workspace. "
                "Pass --workspace to specify the path."
            )
    else:
        workspace = Path(workspace)

    if not workspace.exists():
        raise FileNotFoundError(f"Workspace not found: {workspace}")

    results: dict[str, Any] = {"workspace": str(workspace), "created": [], "skipped": [], "wrappers": 0}
    today = _today()

    # --- Config files ---

    # trust.json (at workspace root, OpenClaw convention)
    trust_path = workspace / "trust.json"
    if not trust_path.exists() or not skip_existing:
        template = dict(TRUST_JSON_TEMPLATE)
        template["updatedAt"] = today
        template["advancementHistory"] = [{"from": 0, "to": 1, "date": today, "note": "Ratchet setup"}]
        trust_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
        results["created"].append("trust.json")
    else:
        results["skipped"].append("trust.json (exists)")

    # guardrails.json
    guardrails_path = workspace / "guardrails.json"
    if not guardrails_path.exists() or not skip_existing:
        guardrails_path.write_text(json.dumps(GUARDRAILS_TEMPLATE, indent=2) + "\n", encoding="utf-8")
        results["created"].append("guardrails.json")
    else:
        results["skipped"].append("guardrails.json (exists)")

    # incidents/ directory
    incidents_dir = workspace / "incidents"
    if not incidents_dir.exists():
        incidents_dir.mkdir(parents=True)
        (incidents_dir / "README.md").write_text(
            "# Incidents\n\nLog incidents as INC-NNN-short-description.md.\n",
            encoding="utf-8",
        )
        results["created"].append("incidents/")
    else:
        results["skipped"].append("incidents/ (exists)")

    # memory/ directory
    memory_dir = workspace / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "facts").mkdir(exist_ok=True)

    # research/ directory
    (workspace / "research").mkdir(exist_ok=True)

    # ops/ directory
    (workspace / "ops").mkdir(exist_ok=True)

    # BACKLOG.md
    backlog_path = workspace / "BACKLOG.md"
    if not backlog_path.exists():
        backlog_path.write_text(
            f"# Backlog\n\n| ID | Priority | Description | Status | Created |\n"
            f"|----|----------|-------------|--------|---------|"
            f"\n| BL-001 | P2 | First incident postmortem | Open | {today} |\n",
            encoding="utf-8",
        )
        results["created"].append("BACKLOG.md")
    else:
        results["skipped"].append("BACKLOG.md (exists)")

    # --- Bin wrappers ---
    if install_wrappers:
        bin_dir = workspace / "bin"
        bin_dir.mkdir(exist_ok=True)

        for name, script in WRAPPERS.items():
            wrapper_path = bin_dir / name
            # Back up existing script if it exists and isn't already a Ratchet wrapper
            if wrapper_path.exists():
                existing = wrapper_path.read_text(encoding="utf-8", errors="replace")
                if "Ratchet wrapper" in existing:
                    results["skipped"].append(f"bin/{name} (already Ratchet wrapper)")
                    continue
                else:
                    backup = bin_dir / f"{name}.pre-ratchet"
                    if not backup.exists():
                        wrapper_path.rename(backup)
                        results["created"].append(f"bin/{name}.pre-ratchet (backup)")

            _write(wrapper_path, script.strip() + "\n", executable=True)
            results["wrappers"] += 1
            results["created"].append(f"bin/{name}")

    logger.info(f"OpenClaw setup complete: {len(results['created'])} created, {len(results['skipped'])} skipped")
    return results
