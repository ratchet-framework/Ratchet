"""LLM-powered code generation for Ratchet modules.

Given a natural language description, generates a working RatchetModule
implementation using the module interface contract as context.

The LLM knows what RatchetModule requires and generates code that
implements the lifecycle hooks (initialize, on_heartbeat, on_session_start,
on_session_end) with real logic.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib import request as urlreq

logger = logging.getLogger("ratchet.factory.codegen")


# The contract the LLM must implement against
MODULE_CONTRACT = '''
from ratchet.core.module import RatchetModule

class RatchetModule(ABC):
    """Base class all Ratchet modules implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Module identifier (e.g., 'memory', 'pilot', 'research')."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version string."""
        ...

    @property
    def dependencies(self) -> list[str]:
        """List of required module names. Default: none."""
        return []

    @abstractmethod
    async def initialize(self, agent, config: dict[str, Any]) -> None:
        """Called once when the agent starts. Receive agent ref + module config."""
        ...

    @abstractmethod
    async def on_heartbeat(self) -> Optional[dict[str, Any]]:
        """Called on each heartbeat cycle. Return status dict or None."""
        ...

    async def on_session_start(self, context: dict[str, Any]) -> None:
        """Called when a new session begins."""
        pass

    async def on_session_end(self, context: dict[str, Any]) -> None:
        """Called when a session ends."""
        pass

    async def on_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Called when bus publishes an event this module subscribes to."""
        pass

    async def shutdown(self) -> None:
        """Cleanup on agent shutdown."""
        pass
'''

CODEGEN_SYSTEM_PROMPT = """You are a Python code generator for the Ratchet AI agent framework.

You generate complete, working RatchetModule implementations from natural language descriptions.

RULES:
1. Output ONLY valid Python code. No markdown, no explanation, no preamble, no backticks.
2. The module MUST inherit from ratchet.core.module.RatchetModule
3. The module MUST implement: name (property), version (property), initialize(), on_heartbeat()
4. Use standard library only unless the description specifically requires an external package.
5. Use async def for all lifecycle methods.
6. Include proper logging via logging.getLogger("ratchet.<module_name>")
7. Include a module docstring explaining what it does.
8. Include type hints.
9. Make the module configurable via the config dict passed to initialize().
10. Return meaningful status from on_heartbeat().
11. Use self.agent.bus.publish() to emit events other modules can subscribe to.
12. Use self.agent.bus.subscribe() in initialize() to listen for relevant events.

HERE IS THE BASE CLASS YOUR MODULE MUST IMPLEMENT:
""" + MODULE_CONTRACT + """

EXAMPLE — a minimal but real module:

```python
import logging
import shutil
from typing import Any, Optional

from ratchet.core.module import RatchetModule

logger = logging.getLogger("ratchet.disk_monitor")


class DiskMonitorModule(RatchetModule):
    \"\"\"Monitor disk usage and alert when thresholds are exceeded.\"\"\"

    name = "disk_monitor"
    version = "0.1.0"

    def __init__(self) -> None:
        self.agent = None
        self._threshold_pct = 80
        self._check_path = "/"

    async def initialize(self, agent, config: dict[str, Any]) -> None:
        self.agent = agent
        self._threshold_pct = config.get("threshold_pct", 80)
        self._check_path = config.get("check_path", "/")
        logger.info(f"DiskMonitorModule initialized (threshold: {self._threshold_pct}%)")

    async def on_heartbeat(self) -> Optional[dict[str, Any]]:
        total, used, free = shutil.disk_usage(self._check_path)
        pct = round(used * 100 / total, 1)
        status = "warning" if pct >= self._threshold_pct else "healthy"

        if status == "warning":
            await self.agent.bus.publish("disk_monitor.threshold_exceeded", {
                "path": self._check_path,
                "usage_pct": pct,
                "free_gb": round(free / (1024**3), 1),
            })
            logger.warning(f"Disk usage at {pct}% (threshold: {self._threshold_pct}%)")

        return {
            "status": status,
            "usage_pct": pct,
            "free_gb": round(free / (1024**3), 1),
            "threshold_pct": self._threshold_pct,
        }
```

Generate code for the following description. Output ONLY the Python code, nothing else."""


def _call_anthropic(prompt: str, api_key: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Direct Anthropic API call."""
    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": CODEGEN_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urlreq.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urlreq.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["content"][0]["text"]


def _clean_code(raw: str) -> str:
    """Strip markdown fences and preamble from LLM output."""
    # Remove markdown code fences
    if "```python" in raw:
        raw = raw.split("```python", 1)[1]
    if "```" in raw:
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()


def _extract_class_name(code: str) -> str | None:
    """Extract the class name from generated code."""
    m = re.search(r"class\s+(\w+Module)\s*\(", code)
    return m.group(1) if m else None


def _extract_module_name(code: str) -> str | None:
    """Extract the module name property from generated code."""
    m = re.search(r'name\s*=\s*["\'](\w+)["\']', code)
    return m.group(1) if m else None


def generate_module_code(
    description: str,
    module_name: str | None = None,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> dict[str, str]:
    """
    Generate a RatchetModule implementation from a description.

    Args:
        description: Natural language description of what the module should do.
        module_name: Optional module name hint (e.g., "disk_monitor").
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
        model: Model to use for generation.

    Returns:
        Dict with keys:
            "code": The generated Python code
            "class_name": Extracted class name (e.g., "DiskMonitorModule")
            "module_name": Extracted module name (e.g., "disk_monitor")

    Raises:
        RuntimeError: If API key is missing or API call fails.
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    prompt = f"Module description: {description}"
    if module_name:
        prompt += f"\nModule name: {module_name}"

    logger.info(f"Generating module code for: {description[:80]}")

    raw = _call_anthropic(prompt, api_key, model)
    code = _clean_code(raw)

    class_name = _extract_class_name(code)
    extracted_name = _extract_module_name(code)

    if not class_name:
        raise RuntimeError("Generated code does not contain a Module class")

    return {
        "code": code,
        "class_name": class_name,
        "module_name": extracted_name or module_name or "generated",
    }
