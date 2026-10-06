"""The hints: only the last hint may give the answer away, and no hint may give away a puzzle of a later stage."""

from typing import Final

from mystery_forge.answers import normalize_answer
from mystery_forge.checks.game_index import CODE_LIKE_KINDS, mentions, stage_positions
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledPuzzle, Game

# Players of these levels get stuck more often, so one hint leaves them without help too soon.
NEEDS_TWO_HINTS: Final[frozenset[str]] = frozenset({"hard", "expert"})


def check_hints(game: Game) -> list[Finding]:
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        findings.extend(own_answer_findings(puzzle, game.config.language))
        findings.extend(later_answer_findings(game, puzzle))
        if game.config.assistance.hints:
            findings.extend(hint_count_findings(puzzle))
    return findings


def own_answer_findings(puzzle: AssembledPuzzle, language: str) -> list[Finding]:
    forbidden: list[str] = [
        *puzzle.accepted_normalized,
        *(normalize_answer(near_miss.answer, language) for near_miss in puzzle.source.near_misses),
    ]
    findings: list[Finding] = []
    for index, hint in enumerate(puzzle.source.hints[:-1]):
        found: str | None = next((answer for answer in forbidden if mentions(hint.text, answer)), None)
        if found is not None:
            findings.append(
                Finding(
                    severity="error",
                    rule="hints.reveals_answer",
                    message=f"Hint {hint.level} of {puzzle.source.id} contains '{found}', an answer or a near miss "
                    "of the puzzle. Only the last hint may give the answer.",
                    file=puzzle.file,
                    path=f"hints.{index}.text",
                    fix_hint="Point to the method or the document in this hint, and keep the answer for the last one.",
                )
            )
    return findings


def later_answer_findings(game: Game, puzzle: AssembledPuzzle) -> list[Finding]:
    positions: dict[str, int] = stage_positions(game)
    position: int | None = positions.get(puzzle.source.stage)
    if position is None:
        return []
    later: list[AssembledPuzzle] = [
        other
        for other in game.puzzles
        if positions.get(other.source.stage, -1) > position and other.source.answer_format.kind in CODE_LIKE_KINDS
    ]
    findings: list[Finding] = []
    for index, hint in enumerate(puzzle.source.hints):
        for other in later:
            found: str | None = next(
                (answer for answer in other.accepted_normalized if mentions(hint.text, answer)), None
            )
            if found is not None:
                findings.append(
                    Finding(
                        severity="error",
                        rule="hints.reveals_later_answer",
                        message=f"Hint {hint.level} of {puzzle.source.id} contains '{found}', the answer of "
                        f"{other.source.id} in the later stage {other.source.stage}.",
                        file=puzzle.file,
                        path=f"hints.{index}.text",
                        fix_hint="Rephrase the hint so that it does not name the answer of a later puzzle.",
                    )
                )
    return findings


def hint_count_findings(puzzle: AssembledPuzzle) -> list[Finding]:
    if len(puzzle.source.hints) >= 2 or puzzle.source.difficulty not in NEEDS_TWO_HINTS:
        return []
    return [
        Finding(
            severity="warning",
            rule="hints.too_few",
            message=f"The {puzzle.source.difficulty} puzzle {puzzle.source.id} has only one hint.",
            file=puzzle.file,
            path="hints",
            fix_hint="Add a second or third hint: first where to look, then the method, then the answer.",
        )
    ]
