"""Checks of the rendered pages: what players will really hold, read back from the browser.

The game checks read the assembled text. Rendering can still break a puzzle (a font or a CSS rule that changes a
letter) or show an answer in a place that the assembled text does not have (a cover sheet, a header). These checks
read the text and the artifacts of the rendered materials.
"""

from collections.abc import Mapping
from typing import Any

from mystery_forge.checks.game_index import mentions, squash
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledPuzzle, Game
from mystery_forge.mechanics.base import MechanicContext, MechanicImplementation, RenderedArtifact, parse_params
from mystery_forge.render.game_renderer import RenderReport

LEAK_CHECKED_KINDS: frozenset[str] = frozenset({"word", "phrase", "number", "digits"})
SPOILER_ROLES: frozenset[str] = frozenset({"register", "register-results"})


def check_rendered(
    game: Game, report: RenderReport, implementations: Mapping[str, MechanicImplementation[Any]]
) -> list[Finding]:
    return [*roundtrip_findings(game, report, implementations), *rendered_leak_findings(game, report)]


def roundtrip_findings(
    game: Game, report: RenderReport, implementations: Mapping[str, MechanicImplementation[Any]]
) -> list[Finding]:
    """Decode every printed artifact from the page and compare it with the answer."""
    documents: dict[str, str] = {document.meta.id: document.text for document in game.documents}
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        implementation: MechanicImplementation[Any] | None = implementations.get(puzzle.source.mechanic)
        if puzzle.artifact is None or not puzzle.artifact.html or implementation is None:
            continue
        rendered: RenderedArtifact | None = report.artifacts.get(puzzle.source.id)
        if rendered is None:
            findings.append(
                render_finding(
                    "render.artifact_missing",
                    f"The printed materials do not show the material of {puzzle.code}.",
                    puzzle.file,
                    "Place {{artifact}} in the document whose front matter names this puzzle.",
                )
            )
            continue
        if implementation.decode_rendered is None:
            continue
        context = MechanicContext(
            puzzle_id=puzzle.source.id,
            answer=puzzle.source.answer,
            language=game.config.language,
            seed=puzzle.source.seed,
            documents=documents,
        )
        decoded: str = implementation.decode_rendered(
            rendered, parse_params(implementation, puzzle.source.params), context
        )
        if squash(puzzle.source.answer) not in squash(decoded):
            findings.append(
                render_finding(
                    "render.roundtrip",
                    f"The printed material of {puzzle.code} decodes to '{decoded[:80]}', not to the answer.",
                    puzzle.file,
                    "Check the params and the answer against `forge catalog show <mechanic>`.",
                )
            )
    return findings


def rendered_leak_findings(game: Game, report: RenderReport) -> list[Finding]:
    """Find a code-like answer in clear text on a printed page that players have before they solve it."""
    materials = report.outputs.get("materials")
    if materials is None or not materials.sheet_texts:
        return []
    positions: dict[str, int] = {stage.id: index for index, stage in enumerate(game.flow.stages)}
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        if puzzle.source.answer_format.kind not in LEAK_CHECKED_KINDS:
            continue
        limit: int = positions.get(puzzle.source.stage, 0)
        for index, text in enumerate(materials.sheet_texts):
            stage: str | None = materials.sheet_stages[index]
            if materials.sheet_roles[index] in SPOILER_ROLES or positions.get(stage or "", 0) > limit:
                continue
            if leaks_on_sheet(puzzle, text):
                findings.append(
                    render_finding(
                        "render.leak",
                        f"The answer of {puzzle.code} is printed in clear text on materials page {index + 1}.",
                        puzzle.file,
                        "Rewrite that text, or list it in leak_allowlist with a reason if the leak is on purpose.",
                    )
                )
                break
    return findings


def leaks_on_sheet(puzzle: AssembledPuzzle, text: str) -> bool:
    if not mentions(text, squash(puzzle.source.answer)):
        return False
    allowed: list[str] = [squash(entry.text) for entry in puzzle.source.leak_allowlist]
    return not any(entry and entry in squash(text) for entry in allowed)


def render_finding(rule: str, message: str, file: str, fix_hint: str) -> Finding:
    return Finding(severity="error", rule=rule, message=message, file=file, fix_hint=fix_hint)
