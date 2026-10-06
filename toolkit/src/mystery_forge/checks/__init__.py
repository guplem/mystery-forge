"""Whole-game checks that run on the assembled game (`adr/0004-verification-strategy.md`).

Each module is one check family: a pure function of the `Game` (and the mechanic catalog) that returns findings.
"""

from mystery_forge.checks.runner import CHECK_FAMILIES, CHECK_PREFIXES, CheckFamily, run_checks, sort_findings

__all__ = ["CHECK_FAMILIES", "CHECK_PREFIXES", "CheckFamily", "run_checks", "sort_findings"]
