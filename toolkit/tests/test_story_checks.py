import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from mystery_forge.findings import Finding
from mystery_forge.story_checks import check_story_folder

GOLDEN_GAME: Path = Path(__file__).parent / "fixtures" / "golden"


@pytest.fixture
def game_dir(tmp_path: Path) -> Path:
    shutil.copytree(GOLDEN_GAME / "source", tmp_path / "source")
    for name in ("flow.yaml",):
        (tmp_path / "source" / name).unlink()
    shutil.rmtree(tmp_path / "source" / "puzzles")
    shutil.rmtree(tmp_path / "source" / "documents")
    return tmp_path


def story_data(game_dir: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((game_dir / "source" / "story.yaml").read_text(encoding="utf-8"))
    return loaded


def save_story(game_dir: Path, data: dict[str, Any]) -> None:
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    (game_dir / "source" / "story.yaml").write_text(text, encoding="utf-8")


def rules(findings: list[Finding], severity: str = "error") -> list[str]:
    return [finding.rule for finding in findings if finding.severity == severity]


def test_the_golden_story_passes_before_any_puzzle_or_document_exists(game_dir: Path) -> None:
    assert rules(check_story_folder(game_dir)) == []


def test_a_missing_story_or_config_is_reported(game_dir: Path) -> None:
    (game_dir / "source" / "story.yaml").unlink()
    assert rules(check_story_folder(game_dir)) == ["source.missing"]


def test_two_places_at_once_is_an_error(game_dir: Path) -> None:
    data = story_data(game_dir)
    data["timeline"].append(
        {
            "id": "late-walk",
            "start": "1931-03-14 22:00",
            "end": "1931-03-14 23:00",
            "location": "boathouse",
            "participants": ["ana-ruiz"],
            "description": "A walk.",
        }
    )
    save_story(game_dir, data)
    assert "registry.two_places" in rules(check_story_folder(game_dir))


def test_an_innocent_suspect_without_an_exclusion_is_an_error(game_dir: Path) -> None:
    data = story_data(game_dir)
    data["deduction"]["exclusions"] = data["deduction"]["exclusions"][:1]
    save_story(game_dir, data)
    assert "deduction.suspect_not_excluded" in rules(check_story_folder(game_dir))


def test_proofs_reveal_steps_and_exclusions_must_cite_story_clues(game_dir: Path) -> None:
    data = story_data(game_dir)
    data["deduction"]["questions"][0]["proven_by"] = ["no-such-clue"]
    data["reveal"][0]["clues"] = ["ghost-clue"]
    data["deduction"]["exclusions"][0]["clues"] = ["phantom"]
    save_story(game_dir, data)
    found = rules(check_story_folder(game_dir))
    assert found.count("story.clue_unknown") == 3


def test_a_case_file_format_needs_a_deduction(game_dir: Path) -> None:
    data = story_data(game_dir)
    del data["deduction"]
    for character in data["characters"]:
        character.pop("is_culprit", None)
    data["reveal"] = []
    save_story(game_dir, data)
    assert rules(check_story_folder(game_dir)) == ["story.deduction_missing"]
    config_path = game_dir / "source" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["format"] = "envelopes"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    assert rules(check_story_folder(game_dir)) == []


def test_epilogues_must_cover_a_zero_score(game_dir: Path) -> None:
    data = story_data(game_dir)
    data["epilogues"] = [epilogue for epilogue in data["epilogues"] if epilogue["min_score_percent"] > 0]
    save_story(game_dir, data)
    assert rules(check_story_folder(game_dir)) == ["story.epilogue_zero"]


def test_cliche_names_and_phrases_are_warnings(game_dir: Path) -> None:
    data = story_data(game_dir)
    data["characters"][0]["name"] = "Elara Vance"
    data["intro"] = data["intro"] + " A tapestry of secrets awaits."
    save_story(game_dir, data)
    warnings = rules(check_story_folder(game_dir), "warning")
    assert "story.cliche_name" in warnings
    assert "story.cliche_phrase" in warnings


def test_an_intro_outside_the_word_range_is_a_warning(game_dir: Path) -> None:
    data = story_data(game_dir)
    data["intro"] = "Too short."
    save_story(game_dir, data)
    assert "story.intro_length" in rules(check_story_folder(game_dir), "warning")
    data["intro"] = "word " * 300
    save_story(game_dir, data)
    assert "story.intro_length" in rules(check_story_folder(game_dir), "warning")


def test_kids_stories_must_not_mention_murder(game_dir: Path) -> None:
    config_path = game_dir / "source" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["audience"] = "kids"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    data = story_data(game_dir)
    data["truth"] = data["truth"] + " Then he murdered the keeper."
    save_story(game_dir, data)
    assert "story.audience" in rules(check_story_folder(game_dir))


def test_a_kids_story_without_violence_passes_the_audience_check(game_dir: Path) -> None:
    config_path = game_dir / "source" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["audience"] = "kids"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    assert "story.audience" not in rules(check_story_folder(game_dir))


def set_kids_config(game_dir: Path, language: str) -> None:
    config_path = game_dir / "source" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["audience"] = "kids"
    config["language"] = language
    config_path.write_text(json.dumps(config), encoding="utf-8")


@pytest.mark.parametrize(
    ("language", "sentence"),
    [
        ("en", "She sang by the totem while Mordecai skilled the tuerca."),
        ("es", "Ajustó la tuerca y cantó con Mordecai."),
        ("de", "Das Totem stand neben Mordecai."),
        ("fr", "Il a chanté avec Mordecai près du totem."),
    ],
)
def test_harmless_words_do_not_trip_the_death_filter(game_dir: Path, language: str, sentence: str) -> None:
    set_kids_config(game_dir, language)
    data = story_data(game_dir)
    data["truth"] = data["truth"] + " " + sentence
    save_story(game_dir, data)
    assert "story.audience" not in rules(check_story_folder(game_dir))


@pytest.mark.parametrize(
    ("language", "sentence"),
    [
        ("en", "The keeper was dead."),
        ("es", "Encontraron sangre en el suelo."),
        ("ca", "Hi havia sang a terra."),
        ("fr", "Il y avait du sang partout."),
        ("de", "Der Wärter war tot."),
        ("it", "Il guardiano era morto."),
        ("pt", "O guarda estava morto."),
    ],
)
def test_the_death_filter_uses_the_words_of_the_game_language(game_dir: Path, language: str, sentence: str) -> None:
    set_kids_config(game_dir, language)
    data = story_data(game_dir)
    data["truth"] = data["truth"] + " " + sentence
    save_story(game_dir, data)
    assert "story.audience" in rules(check_story_folder(game_dir))


def test_every_language_with_a_checked_table_has_death_words() -> None:
    from mystery_forge.i18n import LANGUAGES
    from mystery_forge.story_checks import DEATH_WORDS

    assert set(DEATH_WORDS) == set(LANGUAGES)


def test_a_language_without_death_words_skips_the_keyword_check(game_dir: Path) -> None:
    config_path = game_dir / "source" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["language"] = "ja"
    config["audience"] = "kids"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    data = story_data(game_dir)
    data["truth"] = "There was a murder in the lighthouse."
    save_story(game_dir, data)
    assert "story.audience" not in rules(check_story_folder(game_dir), "error")


def test_the_intro_length_message_states_the_real_range(game_dir: Path) -> None:
    data = story_data(game_dir)
    data["intro"] = "Too short."
    save_story(game_dir, data)
    message = next(f.message for f in check_story_folder(game_dir) if f.rule == "story.intro_length")
    assert "60 to 200" in message


def test_a_case_file_story_with_too_few_hidden_clues_gets_a_warning(game_dir: Path) -> None:
    data = story_data(game_dir)
    data["clues"] = [clue for clue in data["clues"] if not clue.get("hidden")]
    for question in data["deduction"]["questions"]:
        question["proven_by"] = [clue for clue in question["proven_by"] if any(c["id"] == clue for c in data["clues"])]
        if not question["proven_by"]:
            question["proven_by"] = [data["clues"][0]["id"]]
    save_story(game_dir, data)
    assert "deduction.few_hidden_clues" in rules(check_story_folder(game_dir), "warning")


def test_a_culprit_named_by_elimination_from_plain_clues_is_an_error(game_dir: Path) -> None:
    data = story_data(game_dir)
    hidden = {clue["id"] for clue in data["clues"] if clue.get("hidden")}
    for exclusion in data["deduction"]["exclusions"]:
        exclusion["clues"] = [clue for clue in exclusion["clues"] if clue not in hidden]
    save_story(game_dir, data)
    assert "deduction.culprit_by_elimination" in rules(check_story_folder(game_dir), "error")
