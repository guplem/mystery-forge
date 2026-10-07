from typing import Any

import pytest
from test_checks_support import edit_puzzle, golden_game, golden_mechanics, rules

from mystery_forge.checks.budget import (
    check_budget,
    document_words,
    duration_severity,
    estimate_game_minutes,
    estimate_play_minutes,
    game_play_minutes,
)
from mystery_forge.game import Game


def with_brief(game: Game, **updates: Any) -> Game:
    return game.model_copy(update={"brief": game.brief.model_copy(update=updates)})


def with_duration(minutes: int) -> Game:
    return golden_game().model_copy(
        update={"config": golden_game().config.model_copy(update={"duration_minutes": minutes})}
    )


def test_the_golden_game_fits_its_budget() -> None:
    assert check_budget(golden_game(), golden_mechanics()) == []


def test_the_estimate_adds_puzzles_reading_shared_by_the_players_and_stage_minutes() -> None:
    assert estimate_play_minutes([5, 5, 10], 2, 1, "family", 2, 2400) == pytest.approx(20 + 2400 / 120 / 2 + 10)
    assert estimate_play_minutes([], 4, 2, "adults", 3, 0) == pytest.approx(15)


def test_group_size_solo_play_and_kids_change_the_puzzle_minutes() -> None:
    assert estimate_play_minutes([28], 4, 2, "family", 0, 0) == pytest.approx(28 / 1.6)
    assert estimate_play_minutes([28], 1, 1, "kids", 0, 120) == pytest.approx(28 * 1.25 * 1.4 + 1)


def test_the_game_estimate_reads_the_words_of_the_documents() -> None:
    words: int = document_words(golden_game())
    assert words == sum(len(document.text.split()) for document in golden_game().documents)
    # caesar-cipher easy 5 + arithmetic-lock easy 5 + deduction easy 10, then reading, then 5 minutes per stage.
    expected: float = 20 + words / 120 / 2 + 10
    assert game_play_minutes(golden_game(), golden_mechanics()) == pytest.approx(expected)
    assert estimate_game_minutes(golden_game(), golden_mechanics()) == round(expected)


def test_an_unknown_mechanic_adds_no_puzzle_minutes() -> None:
    game: Game = edit_puzzle(golden_game(), "P3", mechanic="no-such-mechanic")
    assert game_play_minutes(game, golden_mechanics()) == pytest.approx(
        game_play_minutes(golden_game(), golden_mechanics()) - 10
    )


@pytest.mark.parametrize(
    ("estimate", "expected"),
    [(100, None), (110, None), (111, "warning"), (120, "warning"), (121, "error"), (70, None), (69, "error")],
)
def test_the_duration_is_an_error_beyond_20_percent_over_or_30_percent_under(estimate: int, expected: str) -> None:
    assert duration_severity(estimate, 100) == expected


@pytest.mark.parametrize(("duration", "expected"), [(20, ["error"]), (28, ["warning"]), (40, []), (50, ["error"])])
def test_the_game_duration_finding_follows_the_shared_severity(duration: int, expected: list[str]) -> None:
    findings = check_budget(with_duration(duration), golden_mechanics())
    assert [finding.severity for finding in findings] == expected
    assert all(finding.rule == "budget.duration" for finding in findings)


def test_too_many_words_and_a_far_puzzle_count_are_warnings() -> None:
    game: Game = with_brief(golden_game(), reading_words=100, puzzle_count=6)
    findings = check_budget(game, golden_mechanics())
    assert rules(findings) == ["budget.reading", "budget.puzzle_count"]
    assert {finding.severity for finding in findings} == {"warning"}
    assert check_budget(with_brief(golden_game(), puzzle_count=5), golden_mechanics()) == []
