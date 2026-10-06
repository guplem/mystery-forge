"""Answer leaks: a code-like answer must not be readable in any text that players see before they solve the puzzle.

Texts are compared squashed (lowercase letters and digits only), so "B O A T", "b-o-a-t", and "taob" (reversed) all
count. A puzzle's `leak_allowlist` cuts out the passages that contain the answer on purpose.
"""

from dataclasses import dataclass
from typing import Final

from mystery_forge.checks.game_index import (
    CODE_LIKE_KINDS,
    FLOW_FILE,
    MIN_SEARCH_LENGTH,
    STORY_FILE,
    squash,
    stage_positions,
)
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledPuzzle, Game

# Replaces an allowlisted passage. A non-alphanumeric mark keeps the text on both sides from joining into a new match.
CUT_MARK: Final[str] = "|"


@dataclass(frozen=True)
class VisibleText:
    """A text that players can read before they solve a puzzle, with where it lives and the rule for a leak in it."""

    text: str
    label: str
    file: str
    path: str | None
    rule: str


def check_leaks(game: Game) -> list[Finding]:
    positions: dict[str, int] = stage_positions(game)
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        position: int | None = positions.get(puzzle.source.stage)
        if position is None or puzzle.source.answer_format.kind not in CODE_LIKE_KINDS:
            continue
        findings.extend(puzzle_leak_findings(puzzle, visible_texts(game, puzzle, position)))
    return findings


def visible_texts(game: Game, puzzle: AssembledPuzzle, position: int) -> list[VisibleText]:
    """Collect the texts that players can read up to the puzzle's stage, without the puzzle's own artifact text."""
    in_text: str = "leaks.answer_in_text"
    in_title: str = "leaks.answer_in_title"
    texts: list[VisibleText] = [VisibleText(game.story.intro, "the intro", STORY_FILE, "intro", in_text)]
    texts.extend(
        VisibleText(
            stage.opening_text,
            f"the opening text of stage {stage.id}",
            FLOW_FILE,
            f"stages.{index}.opening_text",
            in_text,
        )
        for index, stage in enumerate(game.flow.stages[: position + 1])
        if stage.opening_text
    )
    positions: dict[str, int] = stage_positions(game)
    own_solver_text: str = puzzle.artifact.solver_text if puzzle.artifact is not None else ""
    for document in game.documents:
        if positions.get(document.meta.stage, position + 1) > position:
            continue
        name: str = document.meta.id
        body: str = document.text.replace(own_solver_text, "") if own_solver_text else document.text
        texts.append(VisibleText(body, f"the text of {name}", document.file, None, in_text))
        texts.append(VisibleText(document.meta.title, f"the title of {name}", document.file, "title", in_title))
        texts.extend(
            VisibleText(value, f"the field '{key}' of {name}", document.file, f"fields.{key}", in_title)
            for key, value in document.meta.fields.items()
        )
    texts.append(VisibleText(puzzle.source.title, f"the title of {puzzle.source.id}", puzzle.file, "title", in_title))
    return texts


def puzzle_leak_findings(puzzle: AssembledPuzzle, texts: list[VisibleText]) -> list[Finding]:
    findings: list[Finding] = []
    main_answer: str = puzzle.accepted_normalized[0]
    if len(main_answer) < MIN_SEARCH_LENGTH:
        findings.append(
            Finding(
                severity="warning",
                rule="leaks.short_answer",
                message=f"The answer of {puzzle.source.id} has fewer than {MIN_SEARCH_LENGTH} letters or digits, so "
                "the leak check cannot search for it.",
                file=puzzle.file,
                path="answer",
                fix_hint="Read the documents of this stage and the earlier ones, and make sure no text gives the "
                "answer away.",
            )
        )
    answers: list[str] = [answer for answer in puzzle.accepted_normalized if len(answer) >= MIN_SEARCH_LENGTH]
    allowed: list[str] = [squash(entry.text) for entry in puzzle.source.leak_allowlist]
    used: set[int] = set()
    for visible in texts:
        squashed: str = squash(visible.text)
        for index, passage in enumerate(allowed):
            if passage and passage in squashed:
                used.add(index)
                squashed = squashed.replace(passage, CUT_MARK)
        findings.extend(
            leak_finding(puzzle, visible, answer, reversed_form)
            for answer in answers
            for reversed_form in (False, True)
            if (answer[::-1] if reversed_form else answer) in squashed
            and not (reversed_form and answer == answer[::-1])
        )
    findings.extend(
        Finding(
            severity="warning",
            rule="leaks.allowlist_unused",
            message=f"The allowed leak text '{entry.text}' of {puzzle.source.id} appears in no text that players see "
            "before the puzzle.",
            file=puzzle.file,
            path=f"leak_allowlist.{index}.text",
            fix_hint="Copy the passage word for word from the document, or remove the entry.",
        )
        for index, entry in enumerate(puzzle.source.leak_allowlist)
        if index not in used
    )
    return findings


def leak_finding(puzzle: AssembledPuzzle, visible: VisibleText, answer: str, reversed_form: bool) -> Finding:
    how: str = "reversed " if reversed_form else ""
    return Finding(
        severity="error",
        rule=visible.rule,
        message=f"The answer of {puzzle.source.id} ('{answer}') appears {how}in {visible.label}, which players read "
        "before they solve it.",
        file=visible.file,
        path=visible.path,
        fix_hint=f"Rephrase the text so that it does not contain the answer. If the text must contain it, add the "
        f"passage to `leak_allowlist` in {puzzle.file} with the reason.",
    )
