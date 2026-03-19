"""ratchet.factory — Scaffold, generate, setup, test, and review agents and modules."""

from ratchet.factory.scaffold import scaffold_agent, scaffold_module
from ratchet.factory.codegen import generate_module_code
from ratchet.factory.review import quality_check, generate_tests, run_tests, review_code, QualityReport
from ratchet.factory.setup import setup_openclaw

__all__ = [
    "scaffold_agent", "scaffold_module",
    "generate_module_code",
    "quality_check", "generate_tests", "run_tests", "review_code", "QualityReport",
    "setup_openclaw",
]
