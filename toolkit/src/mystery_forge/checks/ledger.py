"""The evidence ledger: every clue quote is word for word in its document, and every citation names a real clue.

The solver panel and the solutions trust the clues, so a quote that the document does not contain, or a clue that
players only get after the puzzle, breaks the proof that the puzzle is fair.
"""

from collections.abc import Mapping
from typing import Final

from mystery_forge.catalog import Mechanic
from mystery_forge.checks.game_index import (
    STORY_FILE,
    ClueEntry,
    clue_entries,
    documents_by_id,
    stage_positions,
)
from mystery_forge.findings import Finding, Severity
from mystery_forge.game import AssembledDocument, AssembledPuzzle, Game
from mystery_forge.spec.models import Deduction

# Typographic marks (by code point) that an agent and a document may write in different forms. Letters and case stay.
APOSTROPHES: Final[tuple[int, ...]] = (0x2018, 0x2019, 0x201A, 0x201B, 0x2032)
QUOTATION_MARKS: Final[tuple[int, ...]] = (0x201C, 0x201D, 0x201E, 0x201F, 0x2033, 0x00AB, 0x00BB)
DASHES: Final[tuple[int, ...]] = (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212)
TYPOGRAPHIC_MARKS: Final[dict[int, str]] = {
    **dict.fromkeys(APOSTROPHES, "'"),
    **dict.fromkeys(QUOTATION_MARKS, '"'),
    **dict.fromkeys(DASHES, "-"),
}


def check_ledger(game: Game, mechanics: Mapping[str, Mechanic]) -> list[Finding]:
    entries: list[ClueEntry] = clue_entries(game)
    return [
        *duplicate_clue_findings(entries),
        *quote_findings(game, entries),
        *clue_reference_findings(game, {entry.clue.id for entry in entries}),
        *solution_findings(game, mechanics),
        *hint_ladder_findings(game),
    ]


def normalize_quote_text(text: str) -> str:
    return " ".join(text.translate(TYPOGRAPHIC_MARKS).split())


def duplicate_clue_findings(entries: list[ClueEntry]) -> list[Finding]:
    first_files: dict[str, str] = {}
    findings: list[Finding] = []
    for entry in entries:
        first_file: str | None = first_files.get(entry.clue.id)
        if first_file is None:
            first_files[entry.clue.id] = entry.file
            continue
        findings.append(
            Finding(
                severity="error",
                rule="ledger.duplicate_clue_id",
                message=f"The clue id '{entry.clue.id}' already exists in {first_file}.",
                file=entry.file,
                path=f"{entry.path}.id",
                fix_hint="Give the clue an id that no other clue of the game uses, and update its citations.",
            )
        )
    return findings


def quote_findings(game: Game, entries: list[ClueEntry]) -> list[Finding]:
    documents: dict[str, AssembledDocument] = documents_by_id(game)
    positions: dict[str, int] = stage_positions(game)
    findings: list[Finding] = []
    for entry in entries:
        document: AssembledDocument | None = documents.get(entry.clue.document)
        if document is None:
            findings.append(
                Finding(
                    severity="error",
                    rule="ledger.unknown_document",
                    message=f"The clue '{entry.clue.id}' quotes the document {entry.clue.document}, which does not "
                    "exist.",
                    file=entry.file,
                    path=f"{entry.path}.document",
                    fix_hint=f"Use an existing document id: {', '.join(documents)}.",
                )
            )
            continue
        if normalize_quote_text(entry.clue.quote) not in normalize_quote_text(document.text):
            findings.append(
                Finding(
                    severity="error",
                    rule="ledger.quote_not_found",
                    message=f"The quote of the clue '{entry.clue.id}' is not in the text of {document.meta.id}: "
                    f'"{entry.clue.quote}".',
                    file=entry.file,
                    path=f"{entry.path}.quote",
                    fix_hint=f"Copy the quote word for word from {document.file}, or change the document so that "
                    "it contains the quote.",
                )
            )
        if entry.puzzle is not None and is_later_stage(document.meta.stage, entry.puzzle, positions):
            findings.append(
                Finding(
                    severity="error",
                    rule="ledger.clue_too_late",
                    message=f"The clue '{entry.clue.id}' is in {document.meta.id} (stage {document.meta.stage}), "
                    f"but players need it for {entry.puzzle.source.id} in the earlier stage "
                    f"{entry.puzzle.source.stage}.",
                    file=entry.file,
                    path=f"{entry.path}.document",
                    fix_hint="Quote a document of the puzzle's stage or an earlier stage, or move the document.",
                )
            )
    return findings


def is_later_stage(document_stage: str, puzzle: AssembledPuzzle, positions: dict[str, int]) -> bool:
    document_position: int | None = positions.get(document_stage)
    puzzle_position: int | None = positions.get(puzzle.source.stage)
    if document_position is None or puzzle_position is None:
        return False
    return document_position > puzzle_position


def clue_reference_findings(game: Game, known_ids: set[str]) -> list[Finding]:
    """Report each citation of a clue id that no clue defines, with the file and path of the citation."""
    citations: list[tuple[str, str, list[str]]] = []
    for puzzle in game.puzzles:
        citations.extend(
            (puzzle.file, f"solution.{index}.uses", step.uses) for index, step in enumerate(puzzle.source.solution)
        )
        citations.extend(
            (puzzle.file, f"hints.{index}.points_to", hint.points_to) for index, hint in enumerate(puzzle.source.hints)
        )
    deduction: Deduction | None = game.story.deduction
    if deduction is not None:
        citations.extend(
            (STORY_FILE, f"deduction.questions.{index}.proven_by", question.proven_by)
            for index, question in enumerate(deduction.questions)
        )
        citations.extend(
            (STORY_FILE, f"deduction.exclusions.{index}.clues", exclusion.clues)
            for index, exclusion in enumerate(deduction.exclusions)
        )
    citations.extend((STORY_FILE, f"reveal.{index}.clues", step.clues) for index, step in enumerate(game.story.reveal))
    return [
        Finding(
            severity="error",
            rule="ledger.unknown_clue",
            message=f"The clue '{clue_id}' does not exist.",
            file=file,
            path=f"{path}.{position}",
            fix_hint="Cite the id of a clue from story.yaml or from a puzzle file, or add the clue first.",
        )
        for file, path, clue_ids in citations
        for position, clue_id in enumerate(clue_ids)
        if clue_id not in known_ids
    ]


def solution_findings(game: Game, mechanics: Mapping[str, Mechanic]) -> list[Finding]:
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        if any(step.uses for step in puzzle.source.solution):
            continue
        mechanic: Mechanic | None = mechanics.get(puzzle.source.mechanic)
        # A panel puzzle often holds all its material in its own document, so citations are advice there.
        severity: Severity = "warning" if mechanic is not None and mechanic.verification == "panel" else "error"
        findings.append(
            Finding(
                severity=severity,
                rule="ledger.solution_without_clues",
                message=f"No solution step of {puzzle.source.id} cites a clue, so nothing proves that the "
                "documents support the answer.",
                file=puzzle.file,
                path="solution",
                fix_hint="Add the ids of the clues that each step relies on to its `uses` list.",
            )
        )
    return findings


def hint_ladder_findings(game: Game) -> list[Finding]:
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        used: set[str] = {clue_id for step in puzzle.source.solution for clue_id in step.uses}
        previous: set[str] = set()
        for index, hint in enumerate(puzzle.source.hints):
            pointed: set[str] = set(hint.points_to)
            outside: list[str] = sorted(pointed - used)
            if outside:
                findings.append(
                    Finding(
                        severity="warning",
                        rule="ledger.hint_outside_solution",
                        message=f"Hint {hint.level} of {puzzle.source.id} points to clues that the solution does not "
                        f"use: {', '.join(outside)}.",
                        file=puzzle.file,
                        path=f"hints.{index}.points_to",
                        fix_hint="Point hints only to clues that the solution steps use, or add the clue to a step.",
                    )
                )
            dropped: list[str] = sorted(previous - pointed)
            if dropped:
                findings.append(
                    Finding(
                        severity="warning",
                        rule="ledger.hint_ladder_narrows",
                        message=f"Hint {hint.level} of {puzzle.source.id} no longer points to "
                        f"{', '.join(dropped)}, which the hint before it points to.",
                        file=puzzle.file,
                        path=f"hints.{index}.points_to",
                        fix_hint="Let each hint point to the clues of the hint before it, plus new ones.",
                    )
                )
            previous = pointed
    return findings
