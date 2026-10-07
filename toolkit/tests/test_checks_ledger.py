from typing import Any

from test_checks_support import (
    edit_document,
    edit_puzzle,
    edit_story,
    golden_game,
    golden_mechanics,
    only_rule,
    rules,
)

from mystery_forge.checks.ledger import check_ledger, normalize_quote_text
from mystery_forge.game import Game
from mystery_forge.spec.models import Clue, Hint, SolutionStep


def puzzle_clues(game: Game, puzzle_id: str) -> list[Clue]:
    return next(list(puzzle.source.clues) for puzzle in game.puzzles if puzzle.source.id == puzzle_id)


def edit_puzzle_clue(game: Game, puzzle_id: str, index: int, **updates: Any) -> Game:
    clues: list[Clue] = puzzle_clues(game, puzzle_id)
    clues[index] = clues[index].model_copy(update=updates)
    return edit_puzzle(game, puzzle_id, clues=clues)


def test_the_golden_ledger_only_warns_about_narrowing_hint_ladders() -> None:
    findings = check_ledger(golden_game(), golden_mechanics())
    assert rules(findings) == ["ledger.hint_ladder_narrows", "ledger.hint_ladder_narrows"]
    assert [(finding.file, finding.path) for finding in findings] == [
        ("puzzles/P1.yaml", "hints.1.points_to"),
        ("puzzles/P2.yaml", "hints.1.points_to"),
    ]
    assert all(finding.severity == "warning" for finding in findings)


def test_a_clue_id_used_in_two_files_is_an_error_on_the_second_file() -> None:
    game: Game = edit_puzzle_clue(golden_game(), "P3", 1, id="wet-boots")
    findings = only_rule(check_ledger(game, golden_mechanics()), "ledger.duplicate_clue_id")
    assert [(finding.file, finding.path) for finding in findings] == [("puzzles/P3.yaml", "clues.1.id")]
    assert "story.yaml" in findings[0].message


def test_a_clue_in_an_unknown_document_is_an_error() -> None:
    clues: list[Clue] = list(golden_game().story.clues)
    clues[0] = clues[0].model_copy(update={"document": "D9"})
    findings = check_ledger(edit_story(golden_game(), clues=clues), golden_mechanics())
    unknown = only_rule(findings, "ledger.unknown_document")
    assert [(finding.file, finding.path) for finding in unknown] == [("story.yaml", "clues.0.document")]


def test_a_quote_matches_across_whitespace_and_typographic_marks() -> None:
    text: str = (
        golden_game()
        .documents[3]
        .text.replace("Low tide: 1:50", "Low tide:\n\n 1:50")
        .replace("lamp room", f"lamp{chr(0x2011)}room")
    )
    game: Game = edit_document(golden_game(), "D4", text=text)
    game = edit_puzzle_clue(game, "P3", 0, quote="Low  tide: 1:50 in the night")
    game = edit_puzzle_clue(game, "P3", 1, quote="wet boot prints on the lamp-room stairs")
    # Only the story clue still writes "lamp room" with a space, which a hyphen does not match.
    missing = only_rule(check_ledger(game, golden_mechanics()), "ledger.quote_not_found")
    assert [finding.file for finding in missing] == ["story.yaml"]
    curly: str = f"{chr(0x201C)}It{chr(0x2019)}s{chr(0x201D)} {chr(0x2013)} {chr(0xAB)}ok{chr(0xBB)}{chr(0xA0)}now"
    assert normalize_quote_text(curly) == '"It\'s" - "ok" now'


def test_a_quote_that_differs_in_letters_or_case_is_not_found() -> None:
    game: Game = edit_puzzle_clue(golden_game(), "P3", 0, quote="low tide: 1:50 in the night")
    findings = only_rule(check_ledger(game, golden_mechanics()), "ledger.quote_not_found")
    assert [(finding.file, finding.path) for finding in findings] == [("puzzles/P3.yaml", "clues.0.quote")]
    assert findings[0].severity == "error"
    assert "D4" in findings[0].message


def test_a_puzzle_clue_from_a_later_stage_is_an_error() -> None:
    game: Game = edit_puzzle_clue(golden_game(), "P1", 0, document="D4", quote="Low tide: 1:50 in the night")
    findings = only_rule(check_ledger(game, golden_mechanics()), "ledger.clue_too_late")
    assert [(finding.file, finding.path) for finding in findings] == [("puzzles/P1.yaml", "clues.0.document")]


def test_a_clue_in_a_document_of_an_unknown_stage_is_not_judged_too_late() -> None:
    game: Game = edit_document(golden_game(), "D2", meta={"stage": "F"})
    assert only_rule(check_ledger(game, golden_mechanics()), "ledger.clue_too_late") == []


def test_every_clue_reference_must_exist() -> None:
    game: Game = edit_puzzle(
        golden_game(),
        "P1",
        solution=[SolutionStep(text="Decode it.", uses=["no-such-clue"])],
        hints=[Hint(level=1, text="Look.", points_to=["ghost"])],
    )
    deduction = golden_game().story.deduction
    assert deduction is not None
    questions = [deduction.questions[0].model_copy(update={"proven_by": ["wet-boots", "phantom"]})]
    exclusions = [deduction.exclusions[0].model_copy(update={"clues": ["nowhere"]})]
    reveal = [golden_game().story.reveal[0].model_copy(update={"clues": ["missing"]})]
    game = edit_story(
        game,
        deduction=deduction.model_copy(update={"questions": questions, "exclusions": exclusions}),
        reveal=reveal,
    )
    findings = only_rule(check_ledger(game, golden_mechanics()), "ledger.unknown_clue")
    assert [(finding.file, finding.path) for finding in findings] == [
        ("puzzles/P1.yaml", "solution.0.uses.0"),
        ("puzzles/P1.yaml", "hints.0.points_to.0"),
        ("story.yaml", "deduction.questions.0.proven_by.1"),
        ("story.yaml", "deduction.exclusions.0.clues.0"),
        ("story.yaml", "reveal.0.clues.0"),
    ]


def test_a_game_without_a_deduction_has_no_deduction_references() -> None:
    game: Game = edit_story(golden_game(), deduction=None)
    assert only_rule(check_ledger(game, golden_mechanics()), "ledger.unknown_clue") == []


def test_a_solution_without_clues_is_an_error_but_a_warning_for_panel_mechanics() -> None:
    no_clues: list[SolutionStep] = [SolutionStep(text="Work it out.")]
    game: Game = edit_puzzle(golden_game(), "P2", solution=no_clues, hints=[Hint(level=1, text="Think.")])
    game = edit_puzzle(game, "P3", solution=no_clues, hints=[Hint(level=1, text="Think.")])
    findings = only_rule(check_ledger(game, golden_mechanics()), "ledger.solution_without_clues")
    assert [(finding.file, finding.severity) for finding in findings] == [
        ("puzzles/P2.yaml", "error"),
        ("puzzles/P3.yaml", "warning"),
    ]
    unknown_mechanic: Game = edit_puzzle(game, "P3", mechanic="no-such-mechanic")
    findings = only_rule(check_ledger(unknown_mechanic, golden_mechanics()), "ledger.solution_without_clues")
    assert [finding.severity for finding in findings] == ["error", "error"]


def test_a_hint_that_points_outside_the_solution_is_a_warning() -> None:
    hints: list[Hint] = [Hint(level=1, text="See the receipt.", points_to=["coded-line", "receipt-lines"])]
    findings = check_ledger(edit_puzzle(golden_game(), "P1", hints=hints), golden_mechanics())
    outside = only_rule(findings, "ledger.hint_outside_solution")
    assert [(finding.path, finding.severity) for finding in outside] == [("hints.0.points_to", "warning")]
    assert "receipt-lines" in outside[0].message


def test_a_hidden_clue_has_no_quote_to_find_but_needs_an_existing_revealing_puzzle() -> None:
    assert only_rule(check_ledger(golden_game(), golden_mechanics()), "ledger.quote_not_found") == []
    clues: list[Clue] = list(golden_game().story.clues)
    assert clues[4].hidden and clues[5].hidden
    clues[4] = clues[4].model_copy(update={"revealed_by": None})
    clues[5] = clues[5].model_copy(update={"revealed_by": "P9"})
    findings = only_rule(
        check_ledger(edit_story(golden_game(), clues=clues), golden_mechanics()), "ledger.hidden_clue_unrevealed"
    )
    assert [(finding.file, finding.path, finding.severity) for finding in findings] == [
        ("story.yaml", "clues.4.revealed_by", "error"),
        ("story.yaml", "clues.5.revealed_by", "error"),
    ]
    assert "no puzzle" in findings[0].message
    assert "P9" in findings[1].message
