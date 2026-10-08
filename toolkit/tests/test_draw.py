from collections import Counter

import pytest

from mystery_forge.brief import Brief, derive_brief
from mystery_forge.catalog.loader import load_ingredients, load_mechanics
from mystery_forge.config import GameConfig, normalize_config
from mystery_forge.draw import CandidateMechanic, Draw, draw_ingredients, mechanic_fits

ALL_IMPLEMENTED: frozenset[str] = frozenset(mechanic.id for mechanic in load_mechanics())


def make_config(**overrides: object) -> GameConfig:
    raw: dict[str, object] = {"schema_version": 1}
    raw.update(overrides)
    result = normalize_config(raw)
    assert result.config is not None, result.findings
    return result.config


def make_draw(config: GameConfig, seed: int = 7, implemented: frozenset[str] = ALL_IMPLEMENTED) -> Draw:
    brief: Brief = derive_brief(config, seed)
    return draw_ingredients(config, brief, implemented_builders=implemented)


def test_the_draw_is_deterministic_for_a_seed_and_changes_with_the_seed() -> None:
    config = make_config()
    assert make_draw(config, 7) == make_draw(config, 7)
    assert make_draw(config, 7) != make_draw(config, 8)


def test_the_draw_offers_three_settings_two_goals_three_twists_two_frames_and_two_motifs() -> None:
    draw = make_draw(make_config())
    assert len(draw.settings) == 3
    assert len(draw.goals) == 2
    assert len(draw.twists) == 3
    assert len(draw.frames) == 2
    assert len(draw.motifs) == 2
    assert len({setting.id for setting in draw.settings}) == 3


def test_a_surprise_tone_is_drawn_and_a_chosen_tone_is_kept() -> None:
    assert make_draw(make_config(theme={"tone": "noir"})).tone.id == "noir"
    tones = {tone.id for tone in load_ingredients().tones}
    assert make_draw(make_config()).tone.id in tones


def test_settings_fit_the_audience_tone_and_era() -> None:
    config = make_config(audience="family", theme={"tone": "cozy", "era": "historical"})
    draw = make_draw(config)
    eras = {era.id: era.group for era in load_ingredients().eras}
    for setting in draw.settings:
        assert "family" in setting.audiences
        assert "cozy" in setting.tones
        assert any(eras[era] == "historical" for era in setting.era_hints)


def test_the_tone_filter_is_dropped_before_the_era_and_the_audience() -> None:
    config = make_config(audience="kids", theme={"tone": "cozy", "era": "future"})
    draw = make_draw(config)
    eras = {era.id: era.group for era in load_ingredients().eras}
    for setting in draw.settings:
        assert "kids" in setting.audiences
        assert any(eras[era] == "future" for era in setting.era_hints)


def test_goals_and_twists_fit_the_format_and_audience() -> None:
    draw = make_draw(make_config(format="envelopes", audience="teens"))
    for goal in draw.goals:
        assert "envelopes" in goal.formats
        assert "teens" in goal.audiences
    for twist in draw.twists:
        assert "envelopes" in twist.formats
        assert "teens" in twist.audiences


def test_avoided_settings_are_not_drawn_when_others_remain() -> None:
    config = make_config()
    brief = derive_brief(config, 3)
    first = draw_ingredients(config, brief, implemented_builders=ALL_IMPLEMENTED)
    avoided = frozenset(setting.id for setting in first.settings)
    second = draw_ingredients(config, brief, implemented_builders=ALL_IMPLEMENTED, avoid_settings=avoided)
    assert not avoided & {setting.id for setting in second.settings}


def test_when_filters_leave_too_few_cards_the_draw_relaxes_them() -> None:
    config = make_config(audience="kids", theme={"tone": "noir", "era": "fantasy"})
    draw = make_draw(config)
    assert len(draw.settings) == 3


def test_the_draw_carries_the_cliches_and_the_audience_rule() -> None:
    draw = make_draw(make_config(audience="kids"))
    assert draw.cliches.names
    assert draw.audience_rule.allow_murder is False


def test_mechanic_candidates_fit_the_equipment_audience_and_difficulty() -> None:
    config = make_config(
        audience="family", difficulty="easy", equipment={"scissors": False, "printer": "black_and_white"}
    )
    draw = make_draw(config)
    catalog = {mechanic.id: mechanic for mechanic in load_mechanics()}
    assert draw.mechanics
    for candidate in draw.mechanics:
        mechanic = catalog[candidate.id]
        assert not mechanic.needs.scissors
        assert not mechanic.needs.color
        assert "family" in mechanic.audiences
        assert candidate.minutes == mechanic.minutes.easy


def test_mechanic_candidates_are_diverse_and_limit_lookup_ciphers() -> None:
    draw = make_draw(make_config(players={"count": 6}, duration_minutes=180))
    actions = Counter(candidate.player_action for candidate in draw.mechanics)
    assert len(actions) >= 6
    catalog = {mechanic.id: mechanic for mechanic in load_mechanics()}
    assert sum(1 for candidate in draw.mechanics if catalog[candidate.id].lookup_cipher) <= 3
    assert len(draw.mechanics) >= 12


def test_avoided_puzzle_kinds_are_excluded() -> None:
    config = make_config(puzzle_preferences={"words": "avoid", "numbers": "avoid"})
    draw = make_draw(config)
    for candidate in draw.mechanics:
        assert candidate.category not in ("wordplay", "cipher", "math")


def test_unimplemented_built_mechanics_are_not_offered_but_panel_mechanics_are() -> None:
    draw = make_draw(make_config(), implemented=frozenset())
    assert draw.mechanics
    assert {candidate.verification for candidate in draw.mechanics} == {"panel"}


def test_mechanic_fits_rejects_tape_when_there_is_no_tape() -> None:
    config = make_config(equipment={"tape_or_glue": False})
    tape_mechanics = [mechanic for mechanic in load_mechanics() if mechanic.needs.tape]
    assert tape_mechanics
    assert not mechanic_fits(tape_mechanics[0], config, ALL_IMPLEMENTED)


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard", "expert"])
def test_candidate_minutes_follow_the_difficulty(difficulty: str) -> None:
    draw = make_draw(make_config(difficulty=difficulty, audience="puzzle_fans"))
    catalog = {mechanic.id: mechanic for mechanic in load_mechanics()}
    for candidate in draw.mechanics:
        assert candidate.minutes == getattr(catalog[candidate.id].minutes, difficulty)


def test_candidate_mechanic_is_a_small_summary() -> None:
    candidate = make_draw(make_config()).mechanics[0]
    assert isinstance(candidate, CandidateMechanic)
    assert candidate.summary


def test_draw_cards_returns_the_whole_deck_when_it_is_too_small() -> None:
    import random

    from mystery_forge.draw import draw_cards

    assert sorted(draw_cards(["a", "b"], 3, random.Random(1), [lambda card: card == "a"])) == ["a", "b"]


def test_color_mechanics_need_a_color_printer() -> None:
    plain = next(mechanic for mechanic in load_mechanics() if not mechanic.needs.scissors and not mechanic.needs.tape)
    mechanic = plain.model_copy(update={"needs": plain.needs.model_copy(update={"color": True})})
    audience = mechanic.audiences[0]
    difficulty = mechanic.difficulty.min
    base = {"audience": audience, "difficulty": difficulty, "equipment": {"scissors": True, "tape_or_glue": True}}
    assert mechanic_fits(mechanic, make_config(**base), ALL_IMPLEMENTED)
    gray = dict(base, equipment={"scissors": True, "tape_or_glue": True, "printer": "black_and_white"})
    assert not mechanic_fits(mechanic, make_config(**gray), ALL_IMPLEMENTED)


def test_craft_mechanics_are_excluded_when_crafts_are_avoided() -> None:
    draw = make_draw(make_config(puzzle_preferences={"crafts": "avoid"}, equipment={"tape_or_glue": True}))
    catalog = {mechanic.id: mechanic for mechanic in load_mechanics()}
    for candidate in draw.mechanics:
        needs = catalog[candidate.id].needs
        assert not (needs.scissors or needs.tape or needs.fold)


@pytest.mark.parametrize(("language", "fits"), [("en", True), ("pl", True), ("ja", False), ("ru", False)])
def test_a_mechanic_on_the_latin_alphabet_fits_only_a_latin_script_language(language: str, fits: bool) -> None:
    caesar = next(mechanic for mechanic in load_mechanics() if mechanic.id == "caesar-cipher")
    base = {"audience": caesar.audiences[0], "difficulty": caesar.difficulty.min}
    assert mechanic_fits(caesar, make_config(**base, language=language), ALL_IMPLEMENTED) is fits


@pytest.mark.parametrize(("language", "fits"), [("es", True), ("nl", False)])
def test_a_mechanic_that_writes_sentences_fits_only_a_language_with_a_checked_table(language: str, fits: bool) -> None:
    logic = next(mechanic for mechanic in load_mechanics() if mechanic.id == "logic-grid")
    base = {"audience": logic.audiences[0], "difficulty": logic.difficulty.min}
    assert mechanic_fits(logic, make_config(**base, language=language), ALL_IMPLEMENTED) is fits


def test_the_catalog_marks_every_mechanic_that_needs_the_latin_alphabet() -> None:
    marked = {mechanic.id for mechanic in load_mechanics() if mechanic.latin_letters}
    assert marked == {
        "caesar-cipher",
        "atbash-cipher",
        "a1z26-cipher",
        "vigenere-cipher",
        "morse-code",
        "phone-keypad",
        "nato-alphabet",
        "mirror-writing",
        "cryptogram",
        "pigpen-cipher",
        "braille",
        "acrostic",
        "anagram",
        "hidden-every-nth",
        "grid-coordinates",
        "overlay-mask",
        "nonogram",
    }
    assert {mechanic.id for mechanic in load_mechanics() if mechanic.writes_sentences} == {"logic-grid"}
