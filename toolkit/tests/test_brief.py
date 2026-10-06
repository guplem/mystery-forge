import json
from pathlib import Path
from typing import Any

import pytest

from mystery_forge.brief import Brief, Estimate, EstimateInput, derive_brief, estimate_game_size
from mystery_forge.config import GameConfig, normalize_config

CONTRACT_PATH: Path = Path(__file__).resolve().parents[2] / "contracts" / "estimate-vectors.json"
CONTRACT: dict[str, Any] = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def make_config(raw: dict[str, Any]) -> GameConfig:
    config: GameConfig | None = normalize_config({"schema_version": 1, **raw}).config
    assert config is not None
    return config


@pytest.mark.parametrize("vector", CONTRACT["vectors"], ids=lambda vector: vector["name"])
def test_estimate_game_size_matches_the_shared_vectors(vector: dict[str, Any]) -> None:
    result: Estimate = estimate_game_size(EstimateInput(**vector["input"]))
    assert result.model_dump() == vector["expected"]


def test_the_vectors_cover_every_estimate_branch() -> None:
    expected: list[dict[str, int]] = [vector["expected"] for vector in CONTRACT["vectors"]]
    inputs: list[dict[str, Any]] = [vector["input"] for vector in CONTRACT["vectors"]]
    assert {result["puzzle_count"] for result in expected} >= {3, 24}
    assert {result["stage_count"] for result in expected} >= {2, 6}
    assert {result["parallel_width"] for result in expected} == {1, 2, 3, 4}
    assert {given["difficulty"] for given in inputs} == {"easy", "medium", "hard", "expert"}
    assert {given["format"] for given in inputs} == {"envelopes", "case_file", "both"}
    assert {given["quality"] for given in inputs} == {"fast", "best"}
    assert {given["reading_load"] for given in inputs} == {"light", "medium", "heavy"}
    assert {given["players"] for given in inputs} >= {1, 12}
    assert "kids" in {given["audience"] for given in inputs}


def test_derive_brief_maps_the_config_to_the_estimate_and_keeps_the_config_seed() -> None:
    config: GameConfig = make_config(
        {
            "players": {"count": 3},
            "duration_minutes": 60,
            "difficulty": "hard",
            "audience": "teens",
            "format": "envelopes",
            "language": "es",
            "content": {"reading_load": "light"},
            "generation": {"quality": "fast", "seed": 77},
        }
    )
    brief: Brief = derive_brief(config, random_seed=999)
    expected_estimate: Estimate = estimate_game_size(
        EstimateInput(
            players=3,
            duration_minutes=60,
            difficulty="hard",
            audience="teens",
            format="envelopes",
            quality="fast",
            reading_load="light",
        )
    )
    assert brief.model_dump() == {
        **expected_estimate.model_dump(),
        "seed": 77,
        "language": "es",
        "audience": "teens",
        "format": "envelopes",
        "difficulty": "hard",
        "players": 3,
    }


def test_derive_brief_uses_the_random_seed_when_the_config_seed_is_zero() -> None:
    brief: Brief = derive_brief(make_config({}), random_seed=424242)
    assert brief.seed == 424242
    assert brief.solver_count == 5


def test_the_brief_is_frozen() -> None:
    brief: Brief = derive_brief(make_config({}), random_seed=1)
    with pytest.raises(ValueError, match="frozen"):
        brief.seed = 2  # type: ignore[misc]
