"""Scaffold new agents and modules from templates.

Creates directory structures with all the files needed to get started.
No LLM calls — pure template expansion.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ratchet.factory import templates

logger = logging.getLogger("ratchet.factory.scaffold")


def _today() -> str:
    return datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d")


def _slugify(name: str) -> str:
    """Convert a name to a slug: 'My Agent' -> 'my-agent'."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


def _classify(name: str) -> str:
    """Convert a name to PascalCase class name: 'disk-monitor' -> 'DiskMonitorModule'."""
    parts = re.split(r"[-_ ]+", name)
    return "".join(p.capitalize() for p in parts) + "Module"


def _write(path: Path, content: str) -> None:
    """Write a file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.debug(f"  Created: {path}")


def scaffold_agent(
    name: str,
    target_dir: Path | str | None = None,
    timezone_str: str = "America/New_York",
) -> Path:
    """
    Scaffold a new Ratchet agent.

    Creates:
        <name>/
        ├── <name>.py
        ├── config/context.json
        ├── config/trust.json
        ├── config/guardrails.json
        ├── incidents/README.md
        ├── memory/facts/  (empty)
        ├── BACKLOG.md
        ├── NORTH-STAR.md
        ├── README.md
        └── .gitignore

    Args:
        name: Agent name (e.g., "pawl", "my-agent", "Atlas").
        target_dir: Parent directory to create in. Default: current directory.
        timezone_str: Timezone for context.json.

    Returns:
        Path to the created agent directory.
    """
    slug = _slugify(name)
    display_name = name.strip()
    today = _today()
    filename = f"{slug}.py"

    root = Path(target_dir or ".") / slug
    if root.exists():
        raise FileExistsError(f"Directory already exists: {root}")

    fmt = {
        "agent_name": display_name,
        "agent_slug": slug,
        "filename": filename,
        "timezone": timezone_str,
        "today": today,
    }

    _write(root / filename, templates.AGENT_PY.format(**fmt))
    _write(root / "config" / "context.json", templates.CONTEXT_JSON.format(**fmt))
    _write(root / "config" / "trust.json", templates.TRUST_JSON.format(**fmt))
    _write(root / "config" / "guardrails.json", templates.GUARDRAILS_JSON.format(**fmt))
    _write(root / "incidents" / "README.md", templates.INCIDENT_README)
    _write(root / "BACKLOG.md", templates.BACKLOG_MD.format(**fmt))
    _write(root / "NORTH-STAR.md", templates.NORTH_STAR_MD.format(**fmt))
    _write(root / "README.md", templates.README_MD.format(**fmt))
    _write(root / ".gitignore", templates.GITIGNORE)

    # Create empty memory/facts directory
    (root / "memory" / "facts").mkdir(parents=True, exist_ok=True)
    (root / "memory" / "facts" / ".gitkeep").touch()

    logger.info(f"Scaffolded agent '{display_name}' at {root}")
    return root


def scaffold_module(
    name: str,
    description: str = "",
    target_dir: Path | str | None = None,
) -> Path:
    """
    Scaffold a new Ratchet module package.

    Creates:
        packages/ratchet-<name>/
        ├── pyproject.toml
        ├── README.md
        └── src/ratchet/<name>/
            ├── __init__.py
            └── module.py

    Args:
        name: Module name (e.g., "research", "disk-monitor").
        description: One-line description.
        target_dir: Parent directory. Default: current directory.

    Returns:
        Path to the created package directory.
    """
    slug = _slugify(name)
    class_name = _classify(name)
    description = description or f"Ratchet {slug} module"
    import_path = f"ratchet.{slug.replace('-', '_')}"
    module_name = slug.replace("-", "_")

    root = Path(target_dir or ".") / f"ratchet-{slug}"
    if root.exists():
        raise FileExistsError(f"Directory already exists: {root}")

    fmt = {
        "module_name": module_name,
        "class_name": class_name,
        "module_description": description,
        "import_path": import_path,
    }

    src_dir = root / "src" / "ratchet" / module_name

    _write(root / "pyproject.toml", templates.MODULE_PYPROJECT.format(**fmt))
    _write(root / "README.md", templates.MODULE_README.format(**fmt))
    _write(root / "src" / "ratchet" / "__init__.py", templates.MODULE_NAMESPACE_INIT)
    _write(src_dir / "__init__.py", templates.MODULE_INIT_PY.format(**fmt))
    _write(src_dir / "module.py", templates.MODULE_PY.format(**fmt))

    logger.info(f"Scaffolded module 'ratchet-{slug}' at {root}")
    return root
