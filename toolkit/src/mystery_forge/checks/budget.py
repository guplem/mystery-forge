"""The time and reading budget: the game must fit the play time and the reading load that the user asked for.

The estimate follows the brief (`brief.py`): catalog minutes per puzzle for a group of 3 or 4, divided by the speedup
of parallel play, longer for solo players and for kids. Reading time and a few minutes per envelope come on top.
"""

from collections.abc import Mapping
from typing import Final

from mystery_forge.catalog import Mechanic
from mystery_forge.findings import Finding, Severity
from mystery_forge.game import Game

READING_WORDS_PER_MINUTE: Final[int] = 150
MINUTES_PER_STAGE: Final[int] = 5
SOLO_FACTOR: Final[float] = 1.25
KIDS_FACTOR: Final[float] = 1.4
SPEEDUP_PER_EXTRA_WIDTH: Final[float] = 0.6
DURATION_WARNING_SHARE: Final[float] = 0.25
DURATION_ERROR_SHARE: Final[float] = 0.5
READING_WARNING_SHARE: Final[float] = 0.3
PUZZLE_COUNT_TOLERANCE: Final[int] = 2


def check_budget(game: Game, mechanics: Mapping[str, Mechanic]) -> list[Finding]:
    return [*duration_findings(game, mechanics), *reading_findings(game), *puzzle_count_findings(game)]


def document_words(game: Game) -> int:
    return sum(len(document.text.split()) for document in game.documents)


def estimated_minutes(game: Game, mechanics: Mapping[str, Mechanic]) -> float:
    puzzle_minutes: float = sum(
        mechanics[puzzle.source.mechanic].minutes.for_level(puzzle.source.difficulty)
        for puzzle in game.puzzles
        if puzzle.source.mechanic in mechanics
    )
    puzzle_minutes /= 1 + SPEEDUP_PER_EXTRA_WIDTH * (game.brief.parallel_width - 1)
    if game.brief.players == 1:
        puzzle_minutes *= SOLO_FACTOR
    if game.brief.audience == "kids":
        puzzle_minutes *= KIDS_FACTOR
    reading_minutes: float = document_words(game) / READING_WORDS_PER_MINUTE
    return puzzle_minutes + reading_minutes + MINUTES_PER_STAGE * len(game.flow.stages)


def duration_findings(game: Game, mechanics: Mapping[str, Mechanic]) -> list[Finding]:
    estimate: float = estimated_minutes(game, mechanics)
    wanted: int = game.config.duration_minutes
    share: float = abs(estimate - wanted) / wanted
    if share <= DURATION_WARNING_SHARE:
        return []
    severity: Severity = "error" if share > DURATION_ERROR_SHARE else "warning"
    direction: str = "longer" if estimate > wanted else "shorter"
    return [
        Finding(
            severity=severity,
            rule="budget.duration",
            message=f"The game takes about {round(estimate)} minutes, {share:.0%} {direction} than the "
            f"{wanted} minutes in the config.",
            fix_hint="Change the number or the difficulty of the puzzles, or the length of the documents, until "
            "the estimate is near the config duration.",
        )
    ]


def reading_findings(game: Game) -> list[Finding]:
    words: int = document_words(game)
    allowed: int = game.brief.reading_words
    if words <= allowed * (1 + READING_WARNING_SHARE):
        return []
    return [
        Finding(
            severity="warning",
            rule="budget.reading",
            message=f"The documents hold {words} words, more than the reading budget of {allowed} words allows.",
            fix_hint="Shorten the longest documents. Keep every clue quote word for word.",
        )
    ]


def puzzle_count_findings(game: Game) -> list[Finding]:
    count: int = len(game.puzzles)
    planned: int = game.brief.puzzle_count
    if abs(count - planned) <= PUZZLE_COUNT_TOLERANCE:
        return []
    return [
        Finding(
            severity="warning",
            rule="budget.puzzle_count",
            message=f"The game has {count} puzzles, but the brief plans {planned}.",
            fix_hint="Add or remove puzzles to come within 2 of the planned count.",
        )
    ]
