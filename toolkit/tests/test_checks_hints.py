from test_checks_support import edit_assembled_puzzle, edit_config, edit_puzzle, golden_game, rules

from mystery_forge.checks.hints import check_hints
from mystery_forge.game import Game
from mystery_forge.spec.models import AnswerFormat, Hint


def p1_hints(first: str, last: str = "Shift each letter back by three.") -> list[Hint]:
    return [
        Hint(level=1, text=first, points_to=["coded-line"]),
        Hint(level=2, text="Tom explains his code.", points_to=["coded-line", "three-back"]),
        Hint(level=3, text=last, points_to=["coded-line", "three-back"]),
    ]


def test_the_golden_hints_have_no_findings() -> None:
    assert check_hints(golden_game()) == []


def test_an_early_hint_with_the_answer_or_a_near_miss_is_an_error() -> None:
    findings = check_hints(edit_puzzle(golden_game(), "P1", hints=p1_hints("Look in the Boat-House.")))
    assert rules(findings) == ["hints.reveals_answer"]
    assert (findings[0].file, findings[0].path, findings[0].severity) == ("puzzles/P1.yaml", "hints.0.text", "error")
    near_miss = check_hints(edit_puzzle(golden_game(), "P1", hints=p1_hints("Not YXLXQEORPB!")))
    assert rules(near_miss) == ["hints.reveals_answer"]


def test_the_last_hint_may_give_the_answer() -> None:
    hints: list[Hint] = p1_hints("Look at the logbook.", last="It says BOATHOUSE.")
    assert check_hints(edit_puzzle(golden_game(), "P1", hints=hints)) == []


def test_a_short_answer_must_match_a_whole_word() -> None:
    game: Game = edit_assembled_puzzle(golden_game(), "P2", accepted_normalized=["07"])
    flagged = edit_puzzle(game, "P2", hints=[Hint(level=1, text="Dial 07 first."), Hint(level=2, text="Done.")])
    assert rules(check_hints(flagged)) == ["hints.reveals_answer"]
    inside_a_number = edit_puzzle(game, "P2", hints=[Hint(level=1, text="Dial 3074."), Hint(level=2, text="x")])
    assert check_hints(inside_a_number) == []


def test_any_hint_with_the_answer_of_a_later_stage_is_an_error() -> None:
    hints: list[Hint] = p1_hints("Look at the logbook.", last="Think of the low tide.")
    findings = check_hints(edit_puzzle(golden_game(), "P1", hints=hints))
    assert rules(findings) == ["hints.reveals_later_answer"]
    assert findings[0].path == "hints.2.text"
    assert "P3" in findings[0].message


def test_later_answers_that_are_names_or_in_unknown_stages_are_skipped() -> None:
    game: Game = edit_puzzle(golden_game(), "P1", hints=p1_hints("Think of the low tide."))
    assert check_hints(edit_puzzle(game, "P3", answer_format=AnswerFormat(kind="name", label="who"))) == []
    assert check_hints(edit_puzzle(game, "P3", stage="F")) == []
    assert check_hints(edit_puzzle(game, "P1", stage="F")) == []


def test_a_hard_puzzle_with_one_hint_is_a_warning_when_hints_are_on() -> None:
    one_hint: list[Hint] = [Hint(level=1, text="Shift back by three.", points_to=["coded-line"])]
    hard: Game = edit_puzzle(golden_game(), "P1", difficulty="hard", hints=one_hint)
    findings = check_hints(hard)
    assert rules(findings) == ["hints.too_few"]
    assert (findings[0].severity, findings[0].path) == ("warning", "hints")
    assert check_hints(edit_config(hard, "assistance", hints=False)) == []
    assert check_hints(edit_puzzle(hard, "P1", difficulty="medium")) == []
