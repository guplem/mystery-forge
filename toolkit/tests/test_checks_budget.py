from typing import Any

import pytest
from test_checks_support import edit_puzzle, golden_game, golden_mechanics, rules

from mystery_forge.checks.budget import check_budget, document_words, estimated_minutes
from mystery_forge.game import Game


def with_brief(game: Game, **updates: Any) -> Game:
    return game.model_copy(update={"brief": game.brief.model_copy(update=updates)})


def with_duration(minutes: int) -> Game:
    return golden_game().model_copy(
        update={"config": golden_game().config.model_copy(update={"duration_minutes": minutes})}
    )


def test_the_golden_game_runs_a_little_long() -> None:
    findings = check_budget(golden_game(), golden_mechanics())
    assert rules(findings) == ["budget.duration"]
    assert findings[0].severity == "warning"
    assert "30" in findings[0].message


def test_the_estimate_adds_puzzles_reading_and_stage_minutes() -> None:
    words: int = document_words(golden_game())
    assert words == sum(len(document.text.split()) for document in golden_game().documents)
    # caesar-cipher easy 5 + arithmetic-lock easy 5 + deduction medium 18, then reading, then 5 minutes per stage.
    assert estimated_minutes(golden_game(), golden_mechanics()) == pytest.approx(28 + words / 150 + 10)


def test_group_size_solo_play_and_kids_change_the_puzzle_minutes() -> None:
    game: Game = with_brief(golden_game(), parallel_width=2, players=1, audience="kids")
    words: int = document_words(game)
    expected: float = 28 / 1.6 * 1.25 * 1.4 + words / 150 + 10
    assert estimated_minutes(game, golden_mechanics()) == pytest.approx(expected)


def test_an_unknown_mechanic_adds_no_puzzle_minutes() -> None:
    game: Game = edit_puzzle(golden_game(), "P3", mechanic="no-such-mechanic")
    assert estimated_minutes(game, golden_mechanics()) == pytest.approx(
        estimated_minutes(golden_game(), golden_mechanics()) - 18
    )


@pytest.mark.parametrize(
    ("duration", "expected"),
    [(20, ["error"]), (40, []), (90, ["error"]), (60, ["warning"])],
)
def test_the_duration_is_a_warning_beyond_25_percent_and_an_error_beyond_50(duration: int, expected: list[str]) -> None:
    findings = check_budget(with_duration(duration), golden_mechanics())
    assert [finding.severity for finding in findings] == expected
    assert all(finding.rule == "budget.duration" for finding in findings)


def test_too_many_words_and_a_far_puzzle_count_are_warnings() -> None:
    game: Game = with_brief(with_duration(40), reading_words=100, puzzle_count=6)
    findings = check_budget(game, golden_mechanics())
    assert rules(findings) == ["budget.reading", "budget.puzzle_count"]
    assert {finding.severity for finding in findings} == {"warning"}
    assert check_budget(with_brief(with_duration(40), puzzle_count=5), golden_mechanics()) == []
