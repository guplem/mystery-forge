import re
from importlib import resources
from typing import Any, get_args

import pytest
import yaml
from pydantic import ValidationError

from mystery_forge.catalog import (
    EvidenceType,
    Ingredients,
    Mechanic,
    design_rules_text,
    load_evidence_types,
    load_ingredients,
    load_mechanics,
    mechanic_by_id,
)
from mystery_forge.catalog.models import (
    DIFFICULTY_LEVELS,
    Audience,
    EvidenceCatalog,
    MechanicCatalog,
    Tone,
)

CATALOG_FILES: tuple[str, ...] = ("mechanics.yaml", "ingredients.yaml", "evidence.yaml", "design_rules.md")

# Other toolkit modules (builders, checks, the draw) refer to these ids by name.
REQUIRED_MECHANIC_IDS: tuple[str, ...] = (
    "caesar-cipher",
    "atbash-cipher",
    "a1z26-cipher",
    "vigenere-cipher",
    "morse-code",
    "phone-keypad",
    "nato-alphabet",
    "pigpen-cipher",
    "braille",
    "symbol-substitution",
    "word-search",
    "maze",
    "nonogram",
    "logic-grid",
    "acrostic",
    "anagram",
    "hidden-every-nth",
    "arithmetic-lock",
    "clock-faces",
    "grid-coordinates",
    "book-cipher",
    "cut-strips",
    "overlay-mask",
    "riddle",
    "rebus",
    "deduction",
    "observation",
    "timeline-order",
    "cryptogram",
    "mirror-writing",
)

KEBAB_CASE: re.Pattern[str] = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def valid_mechanic_data(**overrides: Any) -> dict[str, Any]:
    """Return the raw data of one valid mechanic, with some fields replaced."""
    data: dict[str, Any] = {
        "id": "test-shift",
        "name": "Test Shift",
        "category": "cipher",
        "player_action": "decode",
        "lookup_cipher": True,
        "summary": "Letters move along the alphabet.",
        "how_it_works": "Each letter moves 3 places.",
        "material": "A coded note.",
        "answer_kinds": ["word"],
        "needs": {"scissors": False, "tape": False, "fold": False, "color": False},
        "solo": True,
        "parallel": True,
        "audiences": ["kids"],
        "difficulty": {"min": "easy", "max": "medium"},
        "minutes": {"easy": 4, "medium": 8, "hard": 15, "expert": 25},
        "verification": "built",
        "builder": "test-shift",
        "pitfalls": ["The shift is not clued."],
        "hint_ladder": ["Look at the note.", "The letters moved.", "Shift each letter back 3."],
        "in_world_examples": ["A telegram.", "A diary page."],
        "combines_documents": False,
    }
    data.update(overrides)
    return data


def raw_yaml(file_name: str) -> Any:
    text: str = resources.files("mystery_forge.catalog").joinpath(file_name).read_text(encoding="utf-8")
    return yaml.safe_load(text)


# Package data


@pytest.mark.parametrize("file_name", CATALOG_FILES)
def test_catalog_file_ships_as_package_data(file_name: str) -> None:
    catalog_file = resources.files("mystery_forge.catalog").joinpath(file_name)
    assert catalog_file.is_file()
    assert catalog_file.read_text(encoding="utf-8").strip()


@pytest.mark.parametrize("file_name", CATALOG_FILES)
def test_catalog_file_has_no_em_dash(file_name: str) -> None:
    text: str = resources.files("mystery_forge.catalog").joinpath(file_name).read_text(encoding="utf-8")
    assert "—" not in text


def test_loaders_are_cached() -> None:
    assert load_mechanics() is load_mechanics()
    assert load_ingredients() is load_ingredients()
    assert load_evidence_types() is load_evidence_types()
    assert design_rules_text() is design_rules_text()


# Mechanics


def test_mechanics_load_as_typed_models() -> None:
    mechanics: tuple[Mechanic, ...] = load_mechanics()
    assert all(isinstance(mechanic, Mechanic) for mechanic in mechanics)
    assert len(mechanics) >= 86


def test_mechanic_ids_are_unique_and_kebab_case() -> None:
    ids: list[str] = [mechanic.id for mechanic in load_mechanics()]
    assert len(ids) == len(set(ids))
    assert all(KEBAB_CASE.match(mechanic_id) for mechanic_id in ids)


@pytest.mark.parametrize("mechanic_id", REQUIRED_MECHANIC_IDS)
def test_required_mechanic_id_exists(mechanic_id: str) -> None:
    assert mechanic_by_id(mechanic_id).id == mechanic_id


def test_every_mechanic_difficulty_range_is_ordered() -> None:
    for mechanic in load_mechanics():
        assert DIFFICULTY_LEVELS.index(mechanic.difficulty.min) <= DIFFICULTY_LEVELS.index(mechanic.difficulty.max)


def test_every_mechanic_has_positive_non_decreasing_minutes() -> None:
    for mechanic in load_mechanics():
        minutes: list[int] = [mechanic.minutes.for_level(level) for level in DIFFICULTY_LEVELS]
        assert all(value > 0 for value in minutes), mechanic.id
        assert minutes == sorted(minutes), mechanic.id


def test_every_mechanic_has_a_three_step_hint_ladder() -> None:
    for mechanic in load_mechanics():
        assert len(mechanic.hint_ladder) == 3
        assert all(hint.strip() for hint in mechanic.hint_ladder), mechanic.id


def test_builder_matches_the_verification_level() -> None:
    for mechanic in load_mechanics():
        if mechanic.verification == "panel":
            assert mechanic.builder is None, mechanic.id
        else:
            assert mechanic.builder == mechanic.id, mechanic.id


def test_lookup_ciphers_are_in_the_cipher_category() -> None:
    lookup_ciphers: list[Mechanic] = [mechanic for mechanic in load_mechanics() if mechanic.lookup_cipher]
    assert lookup_ciphers
    assert all(mechanic.category == "cipher" for mechanic in lookup_ciphers)


def test_catalog_offers_enough_kids_mechanics() -> None:
    assert sum(1 for mechanic in load_mechanics() if "kids" in mechanic.audiences) >= 20


def test_catalog_covers_at_least_eight_player_actions() -> None:
    assert len({mechanic.player_action for mechanic in load_mechanics()}) >= 8


def test_catalog_offers_every_verification_level() -> None:
    assert {mechanic.verification for mechanic in load_mechanics()} == {"built", "verified", "panel"}


def test_mechanic_by_id_names_close_matches_for_an_unknown_id() -> None:
    with pytest.raises(KeyError, match="caesar-cipher"):
        mechanic_by_id("caesar-ciper")


def test_mechanic_by_id_lists_the_catalog_command_when_nothing_is_close() -> None:
    with pytest.raises(KeyError, match="forge catalog"):
        mechanic_by_id("zzzzzz")


# Mechanic model rules


def test_valid_mechanic_data_parses() -> None:
    assert Mechanic.model_validate(valid_mechanic_data()).id == "test-shift"


def test_mechanic_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="extra"):
        Mechanic.model_validate(valid_mechanic_data(surprise=True))


def test_mechanic_rejects_an_id_that_is_not_kebab_case() -> None:
    with pytest.raises(ValidationError, match="pattern"):
        Mechanic.model_validate(valid_mechanic_data(id="Test_Shift", builder="Test_Shift"))


def test_mechanic_rejects_an_inverted_difficulty_range() -> None:
    with pytest.raises(ValidationError, match="min"):
        Mechanic.model_validate(valid_mechanic_data(difficulty={"min": "hard", "max": "easy"}))


def test_mechanic_rejects_decreasing_minutes() -> None:
    with pytest.raises(ValidationError, match="non-decreasing"):
        Mechanic.model_validate(valid_mechanic_data(minutes={"easy": 9, "medium": 8, "hard": 15, "expert": 25}))


def test_mechanic_rejects_zero_minutes() -> None:
    with pytest.raises(ValidationError, match="greater than 0"):
        Mechanic.model_validate(valid_mechanic_data(minutes={"easy": 0, "medium": 8, "hard": 15, "expert": 25}))


def test_mechanic_rejects_a_hint_ladder_without_three_steps() -> None:
    with pytest.raises(ValidationError, match="hint_ladder"):
        Mechanic.model_validate(valid_mechanic_data(hint_ladder=["One.", "Two."]))


def test_mechanic_rejects_a_panel_mechanic_with_a_builder() -> None:
    with pytest.raises(ValidationError, match="panel"):
        Mechanic.model_validate(valid_mechanic_data(verification="panel"))


def test_mechanic_rejects_a_built_mechanic_without_its_own_builder() -> None:
    with pytest.raises(ValidationError, match="builder"):
        Mechanic.model_validate(valid_mechanic_data(builder=None))


def test_mechanic_rejects_a_lookup_cipher_outside_the_cipher_category() -> None:
    with pytest.raises(ValidationError, match="lookup_cipher"):
        Mechanic.model_validate(valid_mechanic_data(category="wordplay", player_action="wordplay"))


def test_mechanic_rejects_too_few_in_world_examples() -> None:
    with pytest.raises(ValidationError, match="in_world_examples"):
        Mechanic.model_validate(valid_mechanic_data(in_world_examples=["Only one."]))


def test_mechanic_catalog_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError, match="test-shift"):
        MechanicCatalog.model_validate({"mechanics": [valid_mechanic_data(), valid_mechanic_data()]})


# Ingredients


def test_ingredient_decks_meet_their_minimum_sizes() -> None:
    ingredients: Ingredients = load_ingredients()
    assert len(ingredients.settings) >= 40
    assert len(ingredients.eras) >= 12
    assert len(ingredients.goals) >= 16
    assert len(ingredients.twists) >= 24
    assert len(ingredients.frames) >= 24
    assert len(ingredients.motifs) >= 20
    assert {tone.id for tone in ingredients.tones} == set(get_args(Tone))
    assert set(ingredients.audience_rules) == set(get_args(Audience))
    assert ingredients.cliches.names
    assert ingredients.cliches.phrases
    assert ingredients.cliches.plots


def test_ingredient_ids_are_unique_and_kebab_case_per_deck() -> None:
    ingredients: Ingredients = load_ingredients()
    for deck in (ingredients.settings, ingredients.eras, ingredients.goals, ingredients.twists, ingredients.frames):
        ids: list[str] = [entry.id for entry in deck]
        assert len(ids) == len(set(ids))
        assert all(KEBAB_CASE.match(entry_id) for entry_id in ids)


def test_kids_never_get_murder_and_adults_do() -> None:
    rules = load_ingredients().audience_rules
    assert not rules["kids"].allow_murder
    assert rules["kids"].decoders_preprinted
    assert rules["adults"].allow_murder


def test_kids_can_draw_from_every_deck() -> None:
    ingredients: Ingredients = load_ingredients()
    for deck in (ingredients.settings, ingredients.goals, ingredients.twists, ingredients.frames):
        assert sum(1 for entry in deck if "kids" in entry.audiences) >= 5


def ingredients_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = raw_yaml("ingredients.yaml")
    data.update(overrides)
    return data


def test_every_audience_has_four_settings_in_every_era_group() -> None:
    # The draw offers 3 settings and drops the tone filter before the era filter, so 4 per group keeps a choice.
    ingredients = load_ingredients()
    era_groups = {era.id: era.group for era in ingredients.eras}
    for audience in ("kids", "family", "teens", "adults", "puzzle_fans"):
        for group in ("historical", "modern", "future", "fantasy"):
            fitting = [
                setting
                for setting in ingredients.settings
                if audience in setting.audiences and any(era_groups[era] == group for era in setting.era_hints)
            ]
            assert len(fitting) >= 4, (audience, group)


def test_ingredients_reject_duplicate_ids_in_a_deck() -> None:
    eras: list[dict[str, Any]] = raw_yaml("ingredients.yaml")["eras"]
    with pytest.raises(ValidationError, match="eras"):
        Ingredients.model_validate(ingredients_data(eras=[*eras, eras[0]]))


def test_ingredients_reject_a_setting_with_an_unknown_era() -> None:
    settings: list[dict[str, Any]] = raw_yaml("ingredients.yaml")["settings"]
    broken_setting: dict[str, Any] = {**settings[0], "era_hints": ["stone-age-on-mars"]}
    with pytest.raises(ValidationError, match="stone-age-on-mars"):
        Ingredients.model_validate(ingredients_data(settings=[broken_setting, *settings[1:]]))


def test_ingredients_reject_a_missing_tone() -> None:
    tones: list[dict[str, Any]] = raw_yaml("ingredients.yaml")["tones"]
    with pytest.raises(ValidationError, match="tones"):
        Ingredients.model_validate(ingredients_data(tones=tones[1:]))


def test_ingredients_reject_a_missing_audience_rule() -> None:
    rules: dict[str, Any] = dict(raw_yaml("ingredients.yaml")["audience_rules"])
    del rules["puzzle_fans"]
    with pytest.raises(ValidationError, match="puzzle_fans"):
        Ingredients.model_validate(ingredients_data(audience_rules=rules))


# Evidence


def test_evidence_types_load_with_unique_kebab_ids() -> None:
    evidence_types: tuple[EvidenceType, ...] = load_evidence_types()
    ids: list[str] = [evidence_type.id for evidence_type in evidence_types]
    assert len(ids) >= 20
    assert len(ids) == len(set(ids))
    assert all(KEBAB_CASE.match(evidence_id) for evidence_id in ids)
    assert all(evidence_type.realism_tips and evidence_type.typical_fields for evidence_type in evidence_types)


def test_evidence_catalog_rejects_duplicate_ids() -> None:
    entry: dict[str, Any] = raw_yaml("evidence.yaml")["evidence_types"][0]
    with pytest.raises(ValidationError, match=entry["id"]):
        EvidenceCatalog.model_validate({"evidence_types": [entry, entry]})


# Story variety and the design guide


def catalog_text_outside_the_blocklist() -> str:
    """Return every catalog text that an agent reads as an example, without the cliche blocklist itself."""
    ingredients: dict[str, Any] = raw_yaml("ingredients.yaml")
    del ingredients["cliches"]
    texts: list[str] = [
        yaml.safe_dump(raw_yaml("mechanics.yaml"), allow_unicode=True),
        yaml.safe_dump(raw_yaml("evidence.yaml"), allow_unicode=True),
        yaml.safe_dump(ingredients, allow_unicode=True),
        design_rules_text(),
    ]
    return "\n".join(texts)


def test_cliche_names_never_appear_as_examples_in_the_catalog() -> None:
    text: str = catalog_text_outside_the_blocklist()
    for name in load_ingredients().cliches.names:
        assert not re.search(rf"\b{re.escape(name)}\b", text, flags=re.IGNORECASE), name


def test_cliche_phrases_never_appear_as_examples_in_the_catalog() -> None:
    text: str = catalog_text_outside_the_blocklist().lower()
    for phrase in load_ingredients().cliches.phrases:
        assert phrase.lower() not in text, phrase


def test_design_rules_are_a_short_non_empty_guide() -> None:
    text: str = design_rules_text()
    assert text.startswith("# ")
    assert 0 < len(text.splitlines()) < 300


def test_design_rules_keep_puzzles_load_bearing() -> None:
    text: str = design_rules_text()
    assert "never the decoding method" in text
    assert "State the last step when players cannot guess it" not in text
    for rule in ("never the culprit's own confession", "never a spelled-out formula", "at most 2 puzzles", "has a job"):
        assert rule in text, rule


def test_the_lock_and_the_strips_warn_about_their_known_failures() -> None:
    lock_pitfalls: str = " ".join(mechanic_by_id("arithmetic-lock").pitfalls).lower()
    assert "never the final puzzle when the note states the formula" in lock_pitfalls
    assert "orientation" in " ".join(mechanic_by_id("cut-strips").pitfalls)


def test_a_mechanic_names_the_items_that_players_need_beyond_paper_and_pencils() -> None:
    from mystery_forge.catalog.loader import mechanic_by_id

    assert mechanic_by_id("mirror-writing").needs.items == ["mirror"]
    assert mechanic_by_id("overlay-stack").needs.items == ["light"]
    assert mechanic_by_id("caesar-cipher").needs.items == []
