import html
import re
from typing import Any

import pytest

from mystery_forge.mechanics import symbols
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
    implementation.id: implementation for implementation in symbols.IMPLEMENTATIONS
}
MECHANIC_IDS: list[str] = ["pigpen-cipher", "braille", "symbol-substitution"]
PANGRAM: str = "The quick brown fox jumps over the lazy dog at the mill"


def make_context(answer: str = "mill", seed: int = 7) -> MechanicContext:
    return MechanicContext(puzzle_id="P1", answer=answer, language="en", seed=seed, documents={})


def build(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> Artifact:
    implementation: MechanicImplementation[Any] = IMPLEMENTATIONS[mechanic_id]
    return implementation.build(parse_params(implementation, raw_params), context)


def rendered_from(artifact: Artifact) -> RenderedArtifact:
    return RenderedArtifact(text=html.unescape(re.sub(r"<[^>]+>", "", artifact.html)), html=artifact.html)


def decode(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext, artifact: Artifact) -> str:
    implementation: MechanicImplementation[Any] = IMPLEMENTATIONS[mechanic_id]
    assert implementation.decode_rendered is not None
    return implementation.decode_rendered(rendered_from(artifact), parse_params(implementation, raw_params), context)


def build_error(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> MechanicBuildError:
    with pytest.raises(MechanicBuildError) as raised:
        build(mechanic_id, raw_params, context)
    return raised.value


def glyph_bodies(artifact: Artifact, attribute: str = "data-symbol") -> dict[str, str]:
    """Return the inner SVG of each glyph by its letter."""
    pattern: str = rf'<svg class="mf-glyph" {attribute}="([A-Z])" viewBox="[0-9 ]+">(.*?)</svg>'
    return dict(re.findall(pattern, artifact.html))


# Shared properties of every symbol mechanic.


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_symbol_mechanic_is_registered(mechanic_id: str) -> None:
    assert mechanic_id in all_implementations()


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_symbol_round_trip_reads_the_message_back_from_the_glyphs(mechanic_id: str) -> None:
    context: MechanicContext = make_context()
    params: dict[str, Any] = {"plaintext": "Meet at the old mill", "include_key": True}
    assert decode(mechanic_id, params, context, build(mechanic_id, params, context)) == "MEET AT THE OLD MILL"


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_symbol_round_trip_of_the_answer_alone_equals_the_answer(mechanic_id: str) -> None:
    context: MechanicContext = make_context("Old Mill")
    assert decode(mechanic_id, {}, context, build(mechanic_id, {}, context)) == "OLD MILL"


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_symbol_build_is_deterministic(mechanic_id: str) -> None:
    params: dict[str, Any] = {"plaintext": PANGRAM, "include_key": "true"}
    assert build(mechanic_id, params, make_context()) == build(mechanic_id, params, make_context())


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_symbol_svg_is_print_safe(mechanic_id: str) -> None:
    artifact: Artifact = build(mechanic_id, {"plaintext": PANGRAM, "include_key": True}, make_context())
    assert "currentColor" in artifact.html
    assert "<script" not in artifact.html
    assert "http" not in artifact.html
    assert "style=" not in artifact.html
    assert all(color == "currentColor" for color in re.findall(r'(?:fill|stroke)="([^"n][^"]*)"', artifact.html))
    assert all(css_class.startswith("mf-") for css_class in re.findall(r'class="([^"]+)"', artifact.html))


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_symbol_glyphs_of_the_26_letters_are_distinct(mechanic_id: str) -> None:
    bodies: dict[str, str] = glyph_bodies(build(mechanic_id, {"plaintext": PANGRAM}, make_context()))
    assert len(bodies) == 26
    assert len(set(bodies.values())) == 26


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_symbol_key_shows_every_letter_only_when_asked(mechanic_id: str) -> None:
    with_key: Artifact = build(mechanic_id, {"include_key": True}, make_context())
    without_key: Artifact = build(mechanic_id, {"include_key": False, "key_parts": 1}, make_context())
    assert glyph_bodies(with_key, "data-key-symbol") == glyph_bodies(
        build(mechanic_id, {"plaintext": PANGRAM}, make_context())
    )
    assert "data-key-symbol" not in without_key.html


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_symbol_rejects_digits_a_missing_answer_and_unknown_params(mechanic_id: str) -> None:
    digits: MechanicBuildError = build_error(mechanic_id, {"plaintext": "Mill 12"}, make_context())
    assert digits.message.startswith("The plaintext 'MILL 12' has digits")
    missing: MechanicBuildError = build_error(mechanic_id, {"plaintext": "The bridge"}, make_context())
    assert missing.message == "The plaintext 'THE BRIDGE' does not contain the answer 'mill'."
    assert "include_keys" in build_error(mechanic_id, {"include_keys": True}, make_context()).message


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_symbol_drops_markup_from_the_plaintext(mechanic_id: str) -> None:
    artifact: Artifact = build(mechanic_id, {"plaintext": "<b>mill</b>"}, make_context())
    assert "<b>" not in artifact.html


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_symbol_params_describe_every_field(mechanic_id: str) -> None:
    schema: dict[str, Any] = IMPLEMENTATIONS[mechanic_id].params_model.model_json_schema()
    assert all(field.get("description") for field in schema["properties"].values())


# pigpen-cipher


def test_pigpen_draws_the_grid_and_x_shapes_with_dots() -> None:
    artifact: Artifact = build("pigpen-cipher", {"plaintext": "Aj sw mill"}, make_context())
    bodies: dict[str, str] = glyph_bodies(artifact)
    assert bodies["A"].count("<line") == 2
    assert "<circle" not in bodies["A"]
    assert bodies["J"].count("<line") == 2
    assert bodies["J"].count("<circle") == 1
    assert bodies["S"].count("<polyline") == 1
    assert bodies["W"].count("<circle") == 1
    assert artifact.solver_text == (
        "Symbols: [box: bottom right] [box: bottom right, dot] / [V: opening up] "
        "[V: opening up, dot] / [box: top bottom right, dot] [box: top left] "
        "[box: bottom left, dot] [box: bottom left, dot]"
    )


def test_pigpen_key_lists_every_letter_in_the_solver_text() -> None:
    artifact: Artifact = build("pigpen-cipher", {"include_key": "true"}, make_context())
    assert "\nKey: A = [box: bottom right], B = [box: bottom left right]," in artifact.solver_text
    assert artifact.solver_text.endswith("Z = [V: opening down, dot]")


# braille


def test_braille_fills_the_dots_of_each_letter_and_outlines_the_rest() -> None:
    artifact: Artifact = build("braille", {"plaintext": "Az mill"}, make_context())
    bodies: dict[str, str] = glyph_bodies(artifact)
    assert bodies["A"].count('fill="currentColor"') == 1
    assert bodies["A"].count("<circle") == 6
    assert bodies["Z"].count('fill="currentColor"') == 4
    assert artifact.solver_text == (
        "Symbols: [dots 1] [dots 1-3-5-6] / [dots 1-3-4] [dots 2-4] [dots 1-2-3] [dots 1-2-3]"
    )


def test_braille_key_lists_every_letter_in_the_solver_text() -> None:
    artifact: Artifact = build("braille", {"include_key": True}, make_context())
    assert "\nKey: A = [dots 1], B = [dots 1-2]," in artifact.solver_text
    assert artifact.solver_text.endswith("Z = [dots 1-3-5-6]")


# symbol-substitution


def test_symbol_substitution_prints_the_key_by_default() -> None:
    artifact: Artifact = build("symbol-substitution", {}, make_context())
    assert len(glyph_bodies(artifact, "data-key-symbol")) == 26
    assert artifact.print_notes == ()


def test_symbol_substitution_solver_text_can_be_solved_with_its_legend() -> None:
    artifact: Artifact = build("symbol-substitution", {"plaintext": "Old mill"}, make_context())
    message, legend = artifact.solver_text.split("\nKey: ")
    letter_for: dict[str, str] = {
        description: letter for letter, description in re.findall(r"([A-Z]) = (\[glyph \d+\])", legend)
    }
    assert len(letter_for) == 26
    words: list[str] = message.removeprefix("Symbols: ").split(" / ")
    decoded: list[str] = ["".join(letter_for[glyph] for glyph in re.findall(r"\[glyph \d+\]", word)) for word in words]
    assert decoded == ["OLD", "MILL"]
    assert all(1 <= int(number) <= 32 for number in re.findall(r"glyph (\d+)", legend))


def test_symbol_substitution_needs_its_key_somewhere() -> None:
    with pytest.raises(MechanicBuildError, match="no key"):
        build("symbol-substitution", {"include_key": "false"}, make_context())


@pytest.mark.parametrize("mechanic", ["symbol-substitution", "pigpen-cipher", "braille"])
def test_the_key_can_split_into_parts_for_other_documents(mechanic: str) -> None:
    artifact: Artifact = build(
        mechanic, {"include_key": False, "key_parts": 3, "plaintext": "Old mill"}, make_context()
    )
    assert "data-key-symbol" not in artifact.html
    assert "\nKey:" not in artifact.solver_text
    assert [part.name for part in artifact.parts] == ["key1", "key2", "key3"]
    letters: list[str] = [
        letter
        for part in artifact.parts
        for letter in re.findall(r'<span class="mf-glyph-key-letter">([A-Z])</span>', part.html)
    ]
    assert letters == list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    assert all(part.solver_text.startswith("Key: ") for part in artifact.parts)
    assert artifact.parts[0].solver_text.split(", ")[0].startswith("Key: A = ")
    assert artifact.print_notes == ()


def test_the_key_goes_with_the_message_or_in_parts_not_both() -> None:
    with pytest.raises(MechanicBuildError, match="both"):
        build("pigpen-cipher", {"include_key": True, "key_parts": 2}, make_context())


def test_symbol_substitution_alphabet_depends_on_the_seed() -> None:
    params: dict[str, Any] = {"plaintext": PANGRAM}
    first: dict[str, str] = glyph_bodies(build("symbol-substitution", params, make_context(seed=1)))
    second: dict[str, str] = glyph_bodies(build("symbol-substitution", params, make_context(seed=2)))
    assert first != second
