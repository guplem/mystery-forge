"""The time and reading budget: the game must fit the play time and the reading load that the user asked for.

`estimate_play_minutes` is the one time estimate: the plan step (`plan.py`), the game checks, and the cover all use it,
so they can never disagree. Catalog minutes per puzzle are for a group of 3 or 4; parallel play divides them, and solo
players and kids take longer. Reading time and a few minutes per envelope come on top. Each parallel team reads its own
papers, so the reading splits over the teams, the same way as the reading budget in `brief.py`.
"""

from collections.abc import Mapping, Sequence
from typing import Final

from mystery_forge.brief import READING_WORDS_PER_MINUTE
from mystery_forge.catalog import Mechanic
from mystery_forge.findings import Finding, Severity
from mystery_forge.game import Game

MINUTES_PER_STAGE: Final[int] = 5
SOLO_FACTOR: Final[float] = 1.25
KIDS_FACTOR: Final[float] = 1.4
SPEEDUP_PER_EXTRA_WIDTH: Final[float] = 0.6
DURATION_WARNING_OVER: Final[float] = 0.1
DURATION_ERROR_OVER: Final[float] = 0.2
DURATION_ERROR_UNDER: Final[float] = 0.3
READING_WARNING_SHARE: Final[float] = 0.3
PUZZLE_COUNT_TOLERANCE: Final[int] = 2


def estimate_play_minutes(
    puzzle_minutes: Sequence[float],
    players: int,
    parallel_width: int,
    audience: str,
    stage_count: int,
    reading_words: int,
) -> float:
    """Estimate how long a group plays: solving, then reading, then the minutes to open each envelope."""
    solving: float = sum(puzzle_minutes) / (1 + SPEEDUP_PER_EXTRA_WIDTH * (parallel_width - 1))
    if players == 1:
        solving *= SOLO_FACTOR
    if audience == "kids":
        solving *= KIDS_FACTOR
    reading: float = reading_words / READING_WORDS_PER_MINUTE / parallel_width
    return solving + reading + MINUTES_PER_STAGE * stage_count


def duration_severity(estimate: float, wanted: int) -> Severity | None:
    """Judge an estimate against the config duration. A long game hurts more than a short one."""
    ratio: float = estimate / wanted
    if ratio > 1 + DURATION_ERROR_OVER or ratio < 1 - DURATION_ERROR_UNDER:
        return "error"
    if ratio > 1 + DURATION_WARNING_OVER:
        return "warning"
    return None


def check_budget(game: Game, mechanics: Mapping[str, Mechanic]) -> list[Finding]:
    return [*duration_findings(game, mechanics), *reading_findings(game), *puzzle_count_findings(game)]


def document_words(game: Game) -> int:
    return sum(len(document.text.split()) for document in game.documents)


def game_play_minutes(game: Game, mechanics: Mapping[str, Mechanic]) -> float:
    return estimate_play_minutes(
        puzzle_minutes=[
            mechanics[puzzle.source.mechanic].minutes.for_level(puzzle.source.difficulty)
            for puzzle in game.puzzles
            if puzzle.source.mechanic in mechanics
        ],
        players=game.brief.players,
        parallel_width=game.brief.parallel_width,
        audience=game.brief.audience,
        stage_count=len(game.flow.stages),
        reading_words=document_words(game),
    )


def estimate_game_minutes(game: Game, mechanics: Mapping[str, Mechanic]) -> int:
    """Return the estimated play time in whole minutes, such as for the cover."""
    return round(game_play_minutes(game, mechanics))


def duration_findings(game: Game, mechanics: Mapping[str, Mechanic]) -> list[Finding]:
    estimate: float = game_play_minutes(game, mechanics)
    wanted: int = game.config.duration_minutes
    severity: Severity | None = duration_severity(estimate, wanted)
    if severity is None:
        return []
    share: float = abs(estimate - wanted) / wanted
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
