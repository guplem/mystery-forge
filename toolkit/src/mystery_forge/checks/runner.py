"""Run the whole-game checks on an assembled game and return their findings, errors first.

Each check family owns the rules that start with its prefix, so a caller that passes `only` (the story checks) runs
only the families that can report those rules.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from mystery_forge.catalog import Mechanic, load_mechanics
from mystery_forge.checks.budget import check_budget
from mystery_forge.checks.deduction import check_deduction
from mystery_forge.checks.fact_registry import check_fact_registry
from mystery_forge.checks.graph import check_graph
from mystery_forge.checks.hints import check_hints
from mystery_forge.checks.images import check_images
from mystery_forge.checks.kinds import check_document_kinds
from mystery_forge.checks.leaks import check_leaks
from mystery_forge.checks.ledger import check_ledger
from mystery_forge.checks.references import check_references
from mystery_forge.checks.variety import check_variety
from mystery_forge.findings import Finding
from mystery_forge.game import Game

CheckFunction = Callable[[Game, Mapping[str, Mechanic]], list[Finding]]


@dataclass(frozen=True)
class CheckFamily:
    """A group of checks whose rule ids all start with `prefix` and a dot."""

    prefix: str
    run: CheckFunction


CHECK_FAMILIES: Final[tuple[CheckFamily, ...]] = (
    CheckFamily("graph", lambda game, _: check_graph(game)),
    CheckFamily("ledger", check_ledger),
    CheckFamily("leaks", lambda game, _: check_leaks(game)),
    CheckFamily("hints", lambda game, _: check_hints(game)),
    CheckFamily("registry", lambda game, _: check_fact_registry(game)),
    CheckFamily("deduction", lambda game, _: check_deduction(game)),
    CheckFamily("variety", check_variety),
    CheckFamily("budget", check_budget),
    CheckFamily("references", lambda game, _: check_references(game)),
    CheckFamily("documents", lambda game, _: check_document_kinds(game)),
    CheckFamily("images", lambda game, _: check_images(game)),
)
CHECK_PREFIXES: Final[tuple[str, ...]] = tuple(family.prefix for family in CHECK_FAMILIES)


def run_checks(game: Game, catalog: Sequence[Mechanic] | None = None, only: Sequence[str] = ()) -> list[Finding]:
    """Run every check, or only the rules that start with one of the `only` prefixes (such as "ledger.quote").

    Without a catalog, the checks use the catalog that ships with the package.
    """
    mechanics: dict[str, Mechanic] = {
        mechanic.id: mechanic for mechanic in (catalog if catalog is not None else load_mechanics())
    }
    findings: list[Finding] = [
        finding
        for family in CHECK_FAMILIES
        if not only or any(prefix.split(".")[0] == family.prefix for prefix in only)
        for finding in family.run(game, mechanics)
        if rule_matches(finding.rule, only)
    ]
    return sort_findings(findings)


def rule_matches(rule: str, only: Sequence[str]) -> bool:
    return not only or any(rule == prefix or rule.startswith(f"{prefix}.") for prefix in only)


def sort_findings(findings: list[Finding]) -> list[Finding]:
    """Sort errors first, then by file and line. The sort is stable, so each check keeps its own order."""
    return sorted(
        findings,
        key=lambda finding: (finding.severity != "error", finding.file or "", finding.line or 0),
    )
