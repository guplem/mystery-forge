import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from test_assemble import FAKE_IMPLEMENTATIONS, GOLDEN_GAME

from mystery_forge.answers import answer_hash, normalize_answer
from mystery_forge.assemble import assemble_game
from mystery_forge.game import Game
from mystery_forge.i18n import LANGUAGES, STRINGS
from mystery_forge.render.companion_data import (
    COMPANION_STATIC_FILES,
    build_companion_data,
    build_companion_html,
    script_safe_json,
)


@pytest.fixture(scope="module")
def golden_game(tmp_path_factory: pytest.TempPathFactory) -> Game:
    game_dir: Path = tmp_path_factory.mktemp("golden")
    shutil.copytree(GOLDEN_GAME / "source", game_dir / "source")
    game = assemble_game(game_dir, FAKE_IMPLEMENTATIONS).game
    assert game is not None
    return game


def hashed(text: str, game: Game) -> str:
    return answer_hash(normalize_answer(text, game.config.language), game.salt)


def test_the_data_has_the_framing_texts_of_the_story(golden_game: Game) -> None:
    data = build_companion_data(golden_game)
    assert data["format_version"] == 1
    assert data["title"] == "The Lens of Gull Rock"
    assert data["tagline"] == golden_game.story.tagline
    assert data["intro"] == golden_game.story.intro
    assert data["language"] == "en"
    assert data["salt"] == golden_game.salt
    assert data["duration_minutes"] == golden_game.config.duration_minutes
    assert data["panel_verified"] is True
    assert data["final_puzzle"] == "B1"


def test_the_data_survives_a_json_round_trip(golden_game: Game) -> None:
    data = build_companion_data(golden_game)
    assert json.loads(json.dumps(data)) == data


def test_stages_name_their_envelope_and_open_with_a_puzzle_code(golden_game: Game) -> None:
    stages = build_companion_data(golden_game)["stages"]
    assert stages == [
        {"id": "A", "label": "The keeper's desk", "envelope": "Envelope A", "opens_with": "start", "opening_text": ""},
        {
            "id": "B",
            "label": "The boathouse box",
            "envelope": "Envelope B",
            "opens_with": "A1",
            "opening_text": "Inside the boathouse box you find the boatman's papers.",
        },
    ]


def test_puzzles_hash_every_accepted_answer_and_never_carry_it_in_plain_text_outside_the_solution(
    golden_game: Game,
) -> None:
    puzzles = build_companion_data(golden_game)["puzzles"]
    assert [puzzle["code"] for puzzle in puzzles] == ["A1", "A2", "B1"]
    low_tide = puzzles[2]
    assert low_tide["title"] == "How did the thief reach the rock?"
    assert low_tide["stage"] == "B"
    assert low_tide["answer_format"] == "two words"
    assert low_tide["answer_hashes"] == [hashed("low tide", golden_game), hashed("at low tide", golden_game)]
    assert low_tide["unlocks"] is None
    assert low_tide["solution"]["answer"] == "low tide"
    without_solution: dict[str, Any] = {key: value for key, value in low_tide.items() if key != "solution"}
    assert "low tide" not in json.dumps(without_solution)
    assert "lowtide" not in json.dumps(without_solution)


def test_a_puzzle_that_opens_a_stage_names_that_stage(golden_game: Game) -> None:
    puzzles = build_companion_data(golden_game)["puzzles"]
    assert puzzles[0]["unlocks"] == "B"
    assert puzzles[1]["unlocks"] is None


def test_near_misses_are_hashed_with_their_message(golden_game: Game) -> None:
    keeper_code = build_companion_data(golden_game)["puzzles"][0]
    assert keeper_code["near_misses"] == [
        {
            "hash": hashed("yxlxqeorpb", golden_game),
            "message": "You moved the letters the wrong way. Count back, not forward.",
        }
    ]


def test_hints_and_solution_steps_keep_their_order(golden_game: Game) -> None:
    keeper_code = build_companion_data(golden_game)["puzzles"][0]
    assert [hint["level"] for hint in keeper_code["hints"]] == [1, 2, 3]
    assert keeper_code["hints"][0]["text"] == "Look at the foot of the logbook page."
    assert keeper_code["solution"]["steps"][0] == "The logbook says that the code goes back three steps."
    assert keeper_code["solution"]["answer"] == "boathouse"


def test_the_deduction_hashes_the_correct_option_of_each_question(golden_game: Game) -> None:
    deduction = build_companion_data(golden_game)["deduction"]
    who = deduction["questions"][0]
    assert who["id"] == "who"
    assert who["prompt"] == "Who took the great lens?"
    assert who["points"] == 50
    assert who["options"][1] == {"id": "felix", "text": "Felix Ward, the boatman"}
    assert who["correct_hash"] == answer_hash("who:felix", golden_game.salt)
    assert "correct" not in who


def test_epilogues_come_from_the_highest_threshold_down_and_reveal_steps_keep_their_text(golden_game: Game) -> None:
    data = build_companion_data(golden_game)
    assert [epilogue["min_score_percent"] for epilogue in data["epilogues"]] == [75, 40, 0]
    assert data["epilogues"][0] == {
        "min_score_percent": 75,
        "title": "Case closed",
        "text": "Felix confesses. The lens is back in the lamp room before the next storm.",
    }
    assert data["reveal"][0] == "The thief came by water at night, so it was someone with a boat."


def test_a_game_without_a_deduction_or_a_final_puzzle_has_none(golden_game: Game) -> None:
    story = golden_game.story.model_copy(update={"deduction": None})
    flow = golden_game.flow.model_copy(update={"final_puzzle": None})
    data = build_companion_data(golden_game.model_copy(update={"story": story, "flow": flow}))
    assert data["deduction"] is None
    assert data["final_puzzle"] is None


def test_the_ui_texts_are_the_companion_strings_of_the_game_language(golden_game: Game) -> None:
    config = golden_game.config.model_copy(update={"language": "es"})
    data = build_companion_data(golden_game.model_copy(update={"config": config}))
    assert data["ui"]["tab_hints"] == STRINGS["es"]["companion_tab_hints"]
    assert data["stages"][1]["envelope"] == "Sobre B"
    assert set(data["ui"]) == {key.removeprefix("companion_") for key in STRINGS["en"] if key.startswith("companion_")}


def test_every_language_has_the_same_placeholders_in_each_companion_text() -> None:
    for key, english in STRINGS["en"].items():
        if not key.startswith("companion_"):
            continue
        expected: set[str] = set(re.findall(r"\{(\w+)\}", english))
        for language in LANGUAGES:
            assert set(re.findall(r"\{(\w+)\}", STRINGS[language][key])) == expected, (language, key)


def test_script_safe_json_cannot_close_the_script_tag() -> None:
    text = script_safe_json({"note": "</script><!-- x"})
    assert "</" not in text
    assert "<!--" not in text
    assert json.loads(text) == {"note": "</script><!-- x"}


def test_the_html_inlines_every_static_file_and_the_data(golden_game: Game) -> None:
    html = build_companion_html(golden_game)
    assert html.startswith("<!doctype html>")
    assert '<html lang="en">' in html
    assert "<title>The Lens of Gull Rock</title>" in html
    assert "globalThis.MysteryForgeAnswers" in html
    assert "globalThis.MysteryForgeCompanionLogic" in html
    assert "startCompanionApp" in html
    assert "--paper" in html
    assert "<script src" not in html
    assert '<link rel="stylesheet"' not in html
    data_match = re.search(r'<script type="application/json" id="companion-data">(.*?)</script>', html, re.DOTALL)
    assert data_match is not None
    assert json.loads(data_match.group(1)) == build_companion_data(golden_game)


def test_the_html_escapes_story_text_in_the_title(golden_game: Game) -> None:
    story = golden_game.story.model_copy(update={"title": "Fish & <Chips>"})
    html = build_companion_html(golden_game.model_copy(update={"story": story}))
    assert "<title>Fish &amp; &lt;Chips&gt;</title>" in html


def test_no_static_script_can_close_its_script_tag() -> None:
    from importlib.resources import files

    folder = files("mystery_forge.render").joinpath("companion")
    for name in COMPANION_STATIC_FILES:
        assert "</script" not in folder.joinpath(name).read_text(encoding="utf-8").lower(), name
