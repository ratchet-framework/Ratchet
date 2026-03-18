"""Auto-test generation, execution, and self-review for generated modules.

Layer 3 of Ratchet Factory:
  1. Generate tests for a module's code using an LLM
  2. Run the tests in a subprocess
  3. Self-review: LLM checks for bugs, security issues, style problems
  4. Return a verdict: pass, warn, or fail
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib import request as urlreq

logger = logging.getLogger("ratchet.factory.review")


TEST_GEN_SYSTEM_PROMPT = """You are a Python test generator for the Ratchet AI agent framework.

Given a RatchetModule implementation, generate a complete test file using only the standard library unittest module.

RULES:
1. Output ONLY valid Python code. No markdown, no explanation, no backticks.
2. Use unittest.TestCase and asyncio for async tests.
3. Test that the module:
   - Can be instantiated
   - Has correct name and version properties
   - initialize() runs without error (mock the agent)
   - on_heartbeat() returns a dict with "status" key
   - on_session_start() and on_session_end() don't raise
   - Any module-specific logic works correctly
4. Use unittest.mock for the agent object:
   - agent.workspace = Path(tempdir)
   - agent.bus = Mock with subscribe and publish as AsyncMock
   - agent.config = {}
5. Create a temporary directory for any file operations
6. Clean up temp dirs in tearDown
7. Import the module class directly from the code (assume it's importable)
8. DO NOT test external API calls — mock them
9. Include at least 4 test methods
10. End with: if __name__ == "__main__": unittest.main()

IMPORTANT: The module code will be saved as a file and importable. Generate tests that import from the module file directly using importlib."""


CODE_REVIEW_SYSTEM_PROMPT = """You are a senior Python code reviewer for the Ratchet AI agent framework.

Review the following RatchetModule implementation for:
1. BUGS: Logic errors, missing error handling, potential crashes
2. SECURITY: Credential leaks, injection risks, unsafe file operations
3. STYLE: Missing type hints, poor naming, missing docstrings
4. RATCHET: Does it properly implement the RatchetModule interface? Does it use the event bus correctly?

Output a JSON object with this exact structure:
{
  "verdict": "pass" | "warn" | "fail",
  "bugs": ["description of each bug found"],
  "security": ["description of each security concern"],
  "style": ["description of each style issue"],
  "ratchet": ["description of each framework compliance issue"],
  "summary": "one sentence overall assessment"
}

Output ONLY the JSON. No markdown, no explanation."""


def _call_anthropic(system: str, user: str, api_key: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Direct Anthropic API call."""
    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": system,
        "messages": [{"role": "user", "content": user}],
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
    """Strip markdown fences from LLM output."""
    if "```python" in raw:
        raw = raw.split("```python", 1)[1]
    if "```" in raw:
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()


def _clean_json(raw: str) -> str:
    """Strip markdown fences from JSON output."""
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw.split("```json", 1)[1]
    elif raw.startswith("```"):
        raw = raw.split("```", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()


# --- Test Generation ---

@dataclass
class TestResult:
    """Result of running generated tests."""
    passed: bool = False
    tests_run: int = 0
    failures: int = 0
    errors: int = 0
    output: str = ""
    test_code: str = ""


def generate_tests(
    module_code: str,
    class_name: str,
    module_name: str,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """
    Generate tests for a module implementation.

    Returns the test code as a string.
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    prompt = f"""Module class name: {class_name}
Module name: {module_name}

Module code:
```python
{module_code}
```

Generate a complete unittest test file for this module."""

    logger.info(f"Generating tests for {class_name}")
    raw = _call_anthropic(TEST_GEN_SYSTEM_PROMPT, prompt, api_key, model)
    return _clean_code(raw)


def run_tests(module_code: str, test_code: str, module_name: str) -> TestResult:
    """
    Run generated tests against module code in an isolated temp directory.

    Creates temp files, runs with subprocess, captures output.
    """
    result = TestResult(test_code=test_code)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Write module code
        module_file = tmppath / f"{module_name}.py"
        module_file.write_text(module_code, encoding="utf-8")

        # Write test code
        test_file = tmppath / f"test_{module_name}.py"
        test_code_with_path = f"""import sys
sys.path.insert(0, {str(tmppath)!r})
{test_code}"""
        test_file.write_text(test_code_with_path, encoding="utf-8")

        # Run tests
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"]
                if _has_pytest() else
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(tmppath),
                env={**os.environ, "PYTHONPATH": str(tmppath)},
            )
            result.output = proc.stdout + proc.stderr

            # Parse results from unittest output
            if proc.returncode == 0:
                result.passed = True

            # Try to extract counts
            for line in result.output.splitlines():
                if "Ran " in line and " test" in line:
                    import re
                    m = re.search(r"Ran (\d+) test", line)
                    if m:
                        result.tests_run = int(m.group(1))
                if "FAILED" in line:
                    import re
                    m = re.search(r"failures=(\d+)", line)
                    if m:
                        result.failures = int(m.group(1))
                    m = re.search(r"errors=(\d+)", line)
                    if m:
                        result.errors = int(m.group(1))
                if line.strip() == "OK":
                    result.passed = True

        except subprocess.TimeoutExpired:
            result.output = "ERROR: Tests timed out after 30 seconds"
        except Exception as e:
            result.output = f"ERROR: Failed to run tests: {e}"

    return result


def _has_pytest() -> bool:
    """Check if pytest is available."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


# --- Code Review ---

@dataclass
class ReviewResult:
    """Result of an LLM code review."""
    verdict: str = "pass"  # "pass", "warn", "fail"
    bugs: list[str] = field(default_factory=list)
    security: list[str] = field(default_factory=list)
    style: list[str] = field(default_factory=list)
    ratchet: list[str] = field(default_factory=list)
    summary: str = ""
    raw_response: str = ""


def review_code(
    module_code: str,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> ReviewResult:
    """
    Self-review generated code for bugs, security, style, and framework compliance.
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    logger.info("Running code review")
    raw = _call_anthropic(CODE_REVIEW_SYSTEM_PROMPT, module_code, api_key, model)
    cleaned = _clean_json(raw)

    result = ReviewResult(raw_response=raw)
    try:
        data = json.loads(cleaned)
        result.verdict = data.get("verdict", "warn")
        result.bugs = data.get("bugs", [])
        result.security = data.get("security", [])
        result.style = data.get("style", [])
        result.ratchet = data.get("ratchet", [])
        result.summary = data.get("summary", "")
    except json.JSONDecodeError:
        result.verdict = "warn"
        result.summary = "Could not parse review response"

    return result


# --- Full Pipeline ---

@dataclass
class QualityReport:
    """Combined result of test + review pipeline."""
    test_result: TestResult = field(default_factory=TestResult)
    review_result: ReviewResult = field(default_factory=ReviewResult)

    @property
    def passed(self) -> bool:
        return self.test_result.passed and self.review_result.verdict != "fail"

    @property
    def verdict(self) -> str:
        if not self.test_result.passed:
            return "fail"
        return self.review_result.verdict


def quality_check(
    module_code: str,
    class_name: str,
    module_name: str,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
    skip_tests: bool = False,
    skip_review: bool = False,
) -> QualityReport:
    """
    Run the full quality pipeline: generate tests, run them, review code.

    Args:
        module_code: The generated module code.
        class_name: The module class name.
        module_name: The module name (snake_case).
        api_key: Anthropic API key.
        model: Model for test generation and review.
        skip_tests: Skip test generation and execution.
        skip_review: Skip LLM code review.

    Returns:
        QualityReport with test and review results.
    """
    report = QualityReport()

    if not skip_tests:
        logger.info("Phase 1: Generating and running tests")
        try:
            test_code = generate_tests(module_code, class_name, module_name, api_key, model)
            report.test_result = run_tests(module_code, test_code, module_name)
            report.test_result.test_code = test_code
        except Exception as e:
            report.test_result = TestResult(output=f"Test generation failed: {e}")

    if not skip_review:
        logger.info("Phase 2: Code review")
        try:
            report.review_result = review_code(module_code, api_key, model)
        except Exception as e:
            report.review_result = ReviewResult(
                verdict="warn", summary=f"Review failed: {e}"
            )

    return report
