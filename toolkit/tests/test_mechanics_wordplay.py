import html
import re
from collections.abc import Mapping
from typing import Any

import pytest

from mystery_forge.mechanics import wordplay
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
    parse_params,
)
from mystery_forge.mechanics.registry import all_implementations

IMPLEMENTATIONS: dict[str, MechanicImplementation[Any]] = {
    implementation.id: implementation for implementation in wordplay.IMPLEMENTATIONS
}
MECHANIC_IDS: list[str] = ["acrostic", "anagram", "hidden-every-nth"]


def make_context(documents: Mapping[str, str], answer: str = "mill") -> MechanicContext:
    return MechanicContext(puzzle_id="P1", answer=answer, language="en", seed=7, documents=documents)


def build(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> Artifact:
    implementation: MechanicImplementation[Any] = IMPLEMENTATIONS[mechanic_id]
    return implementation.build(parse_params(implementation, raw_params), context)


def rendered_from(artifact: Artifact) -> RenderedArtifact:
    return RenderedArtifact(text=html.unescape(re.sub(r"<[^>]+>", "", artifact.html)), html=artifact.html)


def build_error(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> MechanicBuildError:
    with pytest.raises(MechanicBuildError) as raised:
        build(mechanic_id, raw_params, context)
    return raised.value


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_wordplay_mechanic_is_registered(mechanic_id: str) -> None:
    assert mechanic_id in all_implementations()


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_wordplay_params_describe_every_field(mechanic_id: str) -> None:
    schema: dict[str, Any] = IMPLEMENTATIONS[mechanic_id].params_model.model_json_schema()
    assert all(field.get("description") for field in schema["properties"].values())


# acrostic

LINES_DOCUMENT: str = "Morning came slowly.\n\n---\nIn the hall, a clock.\nLate again, she said.\nLights went out."


def test_acrostic_accepts_first_letters_of_lines_that_spell_the_answer() -> None:
    artifact: Artifact = build("acrostic", {"document": "poem"}, make_context({"poem": LINES_DOCUMENT}))
    assert artifact == Artifact(html="", solver_text="")


def test_acrostic_reads_last_letters_of_sentences() -> None:
    document: str = "I chew gum. Say hi! It is all? A barn owl."
    context: MechanicContext = make_context({"note": document})
    build("acrostic", {"document": "note", "mode": "sentences", "letter": "last"}, context)


def test_acrostic_reads_first_letters_of_paragraphs() -> None:
    document: str = "Mist rolled in.\nIt was cold.\n\nIn the dark.\n  \nLater on.\n\nLight came."
    build("acrostic", {"document": "diary", "mode": "paragraphs"}, make_context({"diary": document}))


def test_acrostic_rejects_letters_that_do_not_spell_the_answer() -> None:
    document: str = "Xylophones.\n" + LINES_DOCUMENT + "\nYes."
    error: MechanicBuildError = build_error("acrostic", {"document": "poem"}, make_context({"poem": document}))
    assert error.message == "The first letters of the lines spell 'XMILLY', not the answer 'mill'."
    assert "exact" in error.fix_hint


def test_acrostic_accepts_the_answer_inside_the_letters_when_not_exact() -> None:
    document: str = "Xylophones.\n" + LINES_DOCUMENT + "\nYes."
    build("acrostic", {"document": "poem", "exact": "false"}, make_context({"poem": document}))
    error: MechanicBuildError = build_error(
        "acrostic", {"document": "poem", "exact": False}, make_context({"poem": "Yes.\nNo."})
    )
    assert error.message == "The first letters of the lines spell 'YN', which does not contain the answer 'mill'."


def test_acrostic_rejects_an_unknown_document() -> None:
    error: MechanicBuildError = build_error("acrostic", {"document": "poem"}, make_context({"b": "x", "a": "y"}))
    assert error.message == "The document 'poem' does not exist."
    assert error.fix_hint == "Use one of these document ids: a, b."


def test_acrostic_rejects_unknown_modes_and_missing_documents() -> None:
    context: MechanicContext = make_context({"poem": LINES_DOCUMENT})
    assert "mode" in build_error("acrostic", {"document": "poem", "mode": "words"}, context).message
    assert "document" in build_error("acrostic", {}, context).message


# anagram


def decode_anagram(artifact: Artifact, raw_params: dict[str, Any], context: MechanicContext) -> str:
    implementation: MechanicImplementation[Any] = IMPLEMENTATIONS["anagram"]
    assert implementation.decode_rendered is not None
    return implementation.decode_rendered(rendered_from(artifact), parse_params(implementation, raw_params), context)


def test_anagram_shows_each_letter_as_a_tile() -> None:
    artifact: Artifact = build("anagram", {"letters": "Llím"}, make_context({}))
    assert artifact.html == (
        '<div class="mf-anagram"><span class="mf-tile">L</span><span class="mf-tile">L</span>'
        '<span class="mf-tile">I</span><span class="mf-tile">M</span></div>'
    )
    assert artifact.solver_text == "Letter tiles: L L I M"


def test_anagram_ignores_spaces_and_keeps_digits() -> None:
    context: MechanicContext = make_context({}, answer="Room 12")
    artifact: Artifact = build("anagram", {"letters": "2 moor 1"}, context)
    assert artifact.solver_text == "Letter tiles: 2 M O O R 1"


def test_anagram_round_trip_reads_the_tiles_back_as_the_answer() -> None:
    context: MechanicContext = make_context({}, answer="The Old Mill")
    params: dict[str, Any] = {"letters": "Dim Loll"}
    assert decode_anagram(build("anagram", params, context), params, context) == context.normalized_answer


def test_anagram_decode_returns_the_tiles_when_letters_are_missing() -> None:
    damaged: Artifact = Artifact(html='<span class="mf-tile">L</span><span class="mf-tile">I</span>', solver_text="")
    assert decode_anagram(damaged, {"letters": "LLIM"}, make_context({})) == "LI"


def test_anagram_rejects_letters_that_differ_from_the_answer() -> None:
    error: MechanicBuildError = build_error("anagram", {"letters": "LLIX"}, make_context({}))
    assert error.message == "The letters 'LLIX' do not use exactly the letters of the answer 'mill'."
    assert "once" in error.fix_hint


def test_anagram_rejects_letters_in_the_answer_order() -> None:
    error: MechanicBuildError = build_error("anagram", {"letters": "Mi ll"}, make_context({}))
    assert error.message == "The letters 'MILL' spell the answer in order, so they are not scrambled."
    assert "Shuffle" in error.fix_hint


def test_anagram_drops_markup_and_requires_letters() -> None:
    assert "<l>" not in build("anagram", {"letters": "<l>lim"}, make_context({})).html
    assert "letters" in build_error("anagram", {}, make_context({})).message


# hidden-every-nth


def test_hidden_every_nth_letter_from_a_start_position() -> None:
    context: MechanicContext = make_context({"note": "Xm, xi xl-xl!"})
    artifact: Artifact = build("hidden-every-nth", {"document": "note", "n": "2", "start": "2"}, context)
    assert artifact == Artifact(html="", solver_text="")


def test_hidden_every_nth_word_takes_its_first_letter() -> None:
    context: MechanicContext = make_context({"note": "Many dogs, 42 in the long night; lovely eve."})
    build("hidden-every-nth", {"document": "note", "n": 2, "unit": "word"}, context)


def test_hidden_every_nth_rejects_letters_that_do_not_spell_the_answer() -> None:
    context: MechanicContext = make_context({"note": "Xm, xi xl-xl!"})
    error: MechanicBuildError = build_error("hidden-every-nth", {"document": "note", "n": 2}, context)
    assert error.message == "The letters found with n=2, start=1, unit=letter spell 'XXXX', not the answer 'mill'."
    assert "exact" in error.fix_hint


def test_hidden_every_nth_accepts_the_answer_inside_the_letters_when_not_exact() -> None:
    context: MechanicContext = make_context({"note": "Xm, xi xl-xl xy"})
    build("hidden-every-nth", {"document": "note", "n": 2, "start": 2, "exact": False}, context)


def test_hidden_every_nth_rejects_bad_params_and_unknown_documents() -> None:
    context: MechanicContext = make_context({"note": "x"})
    assert "n" in build_error("hidden-every-nth", {"document": "note", "n": 0}, context).message
    assert "start" in build_error("hidden-every-nth", {"document": "note", "start": 0}, context).message
    assert "unit" in build_error("hidden-every-nth", {"document": "note", "unit": "line"}, context).message
    missing: MechanicBuildError = build_error("hidden-every-nth", {"document": "memo"}, context)
    assert missing.message == "The document 'memo' does not exist."
