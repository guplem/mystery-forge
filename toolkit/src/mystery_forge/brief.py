"""The brief: the numbers that drive one generation, derived from a game config.

The configurator shows the same estimate before the user saves the config, so the formula exists twice: here and in
`configurator/configEstimate.js`. `contracts/estimate-vectors.json` keeps both copies equal.

The formula uses decimal factors (1.4, 1.25, 0.6, 0.1). Binary floats round them (6 x 1.4 x 1.25 gives 10.4999...),
so both copies compute in exact integers: minutes in hundredths and the speedup in tenths.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from mystery_forge.config import Audience, Difficulty, GameConfig, GameFormat, Language, Quality, ReadingLoad

BASE_MINUTES_PER_PUZZLE: dict[Difficulty, int] = {"easy": 6, "medium": 9, "hard": 13, "expert": 18}
READING_WORDS_PER_MINUTE: dict[ReadingLoad, int] = {"light": 60, "medium": 100, "heavy": 150}


class EstimateInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    players: int
    duration_minutes: int
    difficulty: Difficulty
    audience: Audience
    format: GameFormat
    quality: Quality
    reading_load: ReadingLoad


class Estimate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    puzzle_count: int
    stage_count: int
    parallel_width: int
    solver_count: Literal[3, 5]
    reading_words: int
    printed_pages: int
    generation_minutes: int
    minutes_per_puzzle: int


class Brief(Estimate):
    seed: int
    language: Language
    audience: Audience
    format: GameFormat
    difficulty: Difficulty
    players: int


def ceil_div(numerator: int, denominator: int) -> int:
    return -(-numerator // denominator)


def estimate_game_size(given: EstimateInput) -> Estimate:
    """Estimate the puzzle count, the stages, the pages, and the generation time for a game."""
    width: int = min(4, max(1, ceil_div(given.players, 2)))
    speedup_tenths: int = 10 + 6 * (width - 1)
    kids_percent: int = 140 if given.audience == "kids" else 100
    solo_percent: int = 125 if given.players == 1 else 100
    minutes_per_puzzle_hundredths: int = BASE_MINUTES_PER_PUZZLE[given.difficulty] * kids_percent * solo_percent // 100
    overhead: int = 5 + given.duration_minutes // 10 + (10 if given.format != "envelopes" else 0)
    available: int = max(10, given.duration_minutes - overhead)
    puzzle_count: int = min(24, max(3, available * speedup_tenths * 10 // minutes_per_puzzle_hundredths))
    stage_count: int = min(6, max(2, ceil_div(puzzle_count, width + 1)))
    best: bool = given.quality == "best"
    return Estimate(
        puzzle_count=puzzle_count,
        stage_count=stage_count,
        parallel_width=width,
        solver_count=5 if best else 3,
        reading_words=given.duration_minutes * READING_WORDS_PER_MINUTE[given.reading_load],
        printed_pages=4 + stage_count + puzzle_count + ceil_div(puzzle_count, 2),
        generation_minutes=20 + puzzle_count * (6 if best else 3) + stage_count * (8 if best else 4),
        minutes_per_puzzle=(minutes_per_puzzle_hundredths + 50) // 100,
    )


def derive_brief(config: GameConfig, random_seed: int) -> Brief:
    """Derive the brief. A config seed of 0 means "random", so the caller passes the random seed to use."""
    estimate: Estimate = estimate_game_size(
        EstimateInput(
            players=config.players.count,
            duration_minutes=config.duration_minutes,
            difficulty=config.difficulty,
            audience=config.audience,
            format=config.format,
            quality=config.generation.quality,
            reading_load=config.content.reading_load,
        )
    )
    return Brief(
        **estimate.model_dump(),
        seed=config.generation.seed or random_seed,
        language=config.language,
        audience=config.audience,
        format=config.format,
        difficulty=config.difficulty,
        players=config.players.count,
    )
