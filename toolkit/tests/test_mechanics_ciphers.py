import html
import re
from typing import Any

import pytest

from mystery_forge.mechanics import ciphers
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
    implementation.id: implementation for implementation in ciphers.IMPLEMENTATIONS
}

# One valid parameter set per mechanic, with a message that contains the answer "mill".
MESSAGE_CASES: list[tuple[str, dict[str, Any]]] = [
    ("caesar-cipher", {"shift": 5, "show_shift": True, "plaintext": "Meet at the old mill."}),
    ("atbash-cipher", {"plaintext": "Meet at the old mill."}),
    ("a1z26-cipher", {"plaintext": "Meet at the old mill."}),
    ("vigenere-cipher", {"keyword": "Lemon", "plaintext": "Meet at the old mill."}),
    ("morse-code", {"include_reference_chart": True, "plaintext": "Meet at the old mill at 9."}),
    ("phone-keypad", {"plaintext": "Meet at the old mill."}),
    ("phone-keypad", {"style": "position", "plaintext": "Meet at the old mill."}),
    ("nato-alphabet", {"plaintext": "Meet at the old mill at 9."}),
    ("nato-alphabet", {"scramble": True, "plaintext": "Meet at the old mill."}),
    ("mirror-writing", {"plaintext": "Meet at the old mill."}),
    ("cryptogram", {"revealed_letters": ["O", "D", "M", "I"], "plaintext": "Meet at the old mill."}),
]


def make_context(answer: str = "mill", seed: int = 7, language: str = "en") -> MechanicContext:
    return MechanicContext(puzzle_id="P1", answer=answer, language=language, seed=seed, documents={})


def build(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> Artifact:
    implementation: MechanicImplementation[Any] = IMPLEMENTATIONS[mechanic_id]
    return implementation.build(parse_params(implementation, raw_params), context)


def rendered_from(artifact: Artifact) -> RenderedArtifact:
    return RenderedArtifact(text=html.unescape(re.sub(r"<[^>]+>", "", artifact.html)), html=artifact.html)


def decode(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext, artifact: Artifact) -> str:
    implementation: MechanicImplementation[Any] = IMPLEMENTATIONS[mechanic_id]
    assert implementation.decode_rendered is not None
    return implementation.decode_rendered(rendered_from(artifact), parse_params(implementation, raw_params), context)


def ciphertext_of(artifact: Artifact) -> str:
    match: re.Match[str] | None = re.search(r'<p class="mf-ciphertext">([^<]*)</p>', artifact.html)
    assert match is not None
    return html.unescape(match.group(1))


def build_error(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> MechanicBuildError:
    with pytest.raises(MechanicBuildError) as raised:
        build(mechanic_id, raw_params, context)
    return raised.value


# Shared properties of every cipher mechanic.


@pytest.mark.parametrize(("mechanic_id", "raw_params"), MESSAGE_CASES)
def test_cipher_is_registered(mechanic_id: str, raw_params: dict[str, Any]) -> None:
    assert mechanic_id in all_implementations()


@pytest.mark.parametrize(("mechanic_id", "raw_params"), MESSAGE_CASES)
def test_cipher_round_trip_decodes_a_message_that_contains_the_answer(
    mechanic_id: str, raw_params: dict[str, Any]
) -> None:
    context: MechanicContext = make_context()
    decoded: str = decode(mechanic_id, raw_params, context, build(mechanic_id, raw_params, context))
    assert context.normalized_answer in re.sub(r"[^a-z0-9]", "", decoded.lower())


@pytest.mark.parametrize(("mechanic_id", "raw_params"), MESSAGE_CASES)
def test_cipher_round_trip_of_the_answer_alone_equals_the_answer(mechanic_id: str, raw_params: dict[str, Any]) -> None:
    context: MechanicContext = make_context("Old Mill")
    params: dict[str, Any] = {key: value for key, value in raw_params.items() if key != "plaintext"}
    decoded: str = decode(mechanic_id, params, context, build(mechanic_id, params, context))
    assert re.sub(r"[^a-z0-9]", "", decoded.lower()) == context.normalized_answer


@pytest.mark.parametrize(("mechanic_id", "raw_params"), MESSAGE_CASES)
def test_cipher_build_is_deterministic(mechanic_id: str, raw_params: dict[str, Any]) -> None:
    assert build(mechanic_id, raw_params, make_context()) == build(mechanic_id, raw_params, make_context())


@pytest.mark.parametrize(("mechanic_id", "raw_params"), MESSAGE_CASES)
def test_cipher_rejects_a_plaintext_without_the_answer(mechanic_id: str, raw_params: dict[str, Any]) -> None:
    error: MechanicBuildError = build_error(
        mechanic_id, {**raw_params, "plaintext": "Meet at the bridge"}, make_context()
    )
    assert error.message == "The plaintext 'MEET AT THE BRIDGE' does not contain the answer 'mill'."
    assert "plaintext" in error.fix_hint


@pytest.mark.parametrize(("mechanic_id", "raw_params"), MESSAGE_CASES)
def test_cipher_escapes_markup_in_the_plaintext(mechanic_id: str, raw_params: dict[str, Any]) -> None:
    artifact: Artifact = build(mechanic_id, {**raw_params, "plaintext": "<b>Mill</b> & <script>"}, make_context())
    assert "<b>" not in artifact.html
    assert "<script" not in artifact.html


@pytest.mark.parametrize(("mechanic_id", "raw_params"), MESSAGE_CASES)
def test_cipher_params_reject_unknown_fields(mechanic_id: str, raw_params: dict[str, Any]) -> None:
    error: MechanicBuildError = build_error(mechanic_id, {**raw_params, "shfit": 3}, make_context())
    assert "shfit" in error.message


@pytest.mark.parametrize(("mechanic_id", "raw_params"), MESSAGE_CASES)
def test_cipher_params_describe_every_field(mechanic_id: str, raw_params: dict[str, Any]) -> None:
    schema: dict[str, Any] = IMPLEMENTATIONS[mechanic_id].params_model.model_json_schema()
    assert all(field.get("description") for field in schema["properties"].values())


# caesar-cipher


def test_caesar_shifts_each_letter_forward() -> None:
    assert ciphertext_of(build("caesar-cipher", {"shift": 3, "plaintext": "ABC"}, make_context("abc"))) == "DEF"


def test_caesar_wraps_around_and_keeps_digits_spaces_and_punctuation() -> None:
    artifact: Artifact = build("caesar-cipher", {"shift": 1, "plaintext": "Zoo at 9, mill!"}, make_context())
    assert ciphertext_of(artifact) == "APP BU 9, NJMM!"
    assert artifact.solver_text == "Ciphertext: APP BU 9, NJMM!"


def test_caesar_coerces_text_params_and_shows_the_shift_key() -> None:
    artifact: Artifact = build("caesar-cipher", {"shift": "3", "show_shift": "true"}, make_context())
    assert ciphertext_of(artifact) == "PLOO"
    assert '<p class="mf-cipher-key">A = D</p>' in artifact.html
    assert artifact.solver_text == "Ciphertext: PLOO\nKey: A = D"


def test_caesar_hides_the_key_by_default() -> None:
    assert "mf-cipher-key" not in build("caesar-cipher", {}, make_context()).html


@pytest.mark.parametrize("shift", [0, 26])
def test_caesar_rejects_a_shift_outside_1_to_25(shift: int) -> None:
    error: MechanicBuildError = build_error("caesar-cipher", {"shift": shift}, make_context())
    assert "shift" in error.message
    assert "caesar-cipher" in error.fix_hint


# atbash-cipher


def test_atbash_mirrors_the_alphabet_and_keeps_other_signs() -> None:
    artifact: Artifact = build("atbash-cipher", {"plaintext": "Abc xyz, mill 7!"}, make_context())
    assert ciphertext_of(artifact) == "ZYX CBA, NROO 7!"
    assert artifact.solver_text == "Ciphertext: ZYX CBA, NROO 7!"


# a1z26-cipher


def test_a1z26_writes_letter_numbers_with_dashes_and_word_slashes() -> None:
    artifact: Artifact = build("a1z26-cipher", {"plaintext": "Abc, mill!"}, make_context())
    assert ciphertext_of(artifact) == "1-2-3 / 13-9-12-12"
    assert artifact.solver_text == "Ciphertext: 1-2-3 / 13-9-12-12"


def test_a1z26_rejects_digits_in_the_plaintext() -> None:
    error: MechanicBuildError = build_error("a1z26-cipher", {"plaintext": "Mill 12"}, make_context())
    assert error.message == "The plaintext 'MILL 12' has digits, which A1Z26 cannot encode."
    assert "words" in error.fix_hint


def test_a1z26_decodes_an_unreadable_number_as_a_question_mark() -> None:
    artifact: Artifact = Artifact(html='<p class="mf-ciphertext">1-99-x / 26</p>', solver_text="")
    assert decode("a1z26-cipher", {}, make_context(), artifact) == "A?? Z"


# vigenere-cipher


def test_vigenere_matches_the_textbook_example_and_skips_non_letters_in_the_key() -> None:
    artifact: Artifact = build(
        "vigenere-cipher", {"keyword": "lémon", "plaintext": "Attack at dawn"}, make_context("dawn")
    )
    assert ciphertext_of(artifact) == "LXFOPV EF RNHR"
    assert artifact.solver_text == "Ciphertext: LXFOPV EF RNHR"


@pytest.mark.parametrize("keyword", ["LEMON 2", "", "!"])
def test_vigenere_rejects_a_keyword_that_is_not_letters_only(keyword: str) -> None:
    error: MechanicBuildError = build_error("vigenere-cipher", {"keyword": keyword}, make_context())
    assert error.message == f"The Vigenere keyword '{keyword}' must be letters only (A-Z)."
    assert "keyword" in error.fix_hint


def test_vigenere_requires_a_keyword() -> None:
    assert "keyword" in build_error("vigenere-cipher", {}, make_context()).message


# morse-code


def test_morse_separates_letters_with_spaces_and_words_with_slashes() -> None:
    artifact: Artifact = build("morse-code", {"plaintext": "SOS, mill 7"}, make_context())
    assert ciphertext_of(artifact) == "... --- ... / -- .. .-.. .-.. / --..."
    assert artifact.solver_text == "Morse code: ... --- ... / -- .. .-.. .-.. / --..."
    assert "mf-morse-chart" not in artifact.html


def test_morse_reference_chart_lists_every_letter_and_digit() -> None:
    artifact: Artifact = build("morse-code", {"include_reference_chart": "yes"}, make_context())
    assert '<table class="mf-morse-chart">' in artifact.html
    assert "<tr><td>A</td><td>.-</td></tr>" in artifact.html
    assert "<tr><td>0</td><td>-----</td></tr>" in artifact.html
    assert artifact.solver_text.endswith(
        "Reference chart: A .-, B -..., C -.-., D -.., E ., F ..-., G --., H ...., "
        "I .., J .---, K -.-, L .-.., M --, N -., O ---, P .--., Q --.-, R .-., "
        "S ..., T -, U ..-, V ...-, W .--, X -..-, Y -.--, Z --.., 0 -----, "
        "1 .----, 2 ..---, 3 ...--, 4 ....-, 5 ....., 6 -...., 7 --..., 8 ---.., "
        "9 ----."
    )


def test_morse_decodes_an_unknown_code_as_a_question_mark() -> None:
    artifact: Artifact = Artifact(html='<p class="mf-ciphertext">...... .- / ...</p>', solver_text="")
    assert decode("morse-code", {}, make_context(), artifact) == "?A S"


# phone-keypad


def test_phone_keypad_multitap_repeats_the_key_once_per_letter_position() -> None:
    artifact: Artifact = build("phone-keypad", {"plaintext": "Hello, mill"}, make_context())
    assert ciphertext_of(artifact) == "44-33-555-555-666 / 6-444-555-555"
    assert artifact.solver_text == "Phone keypad code: 44-33-555-555-666 / 6-444-555-555"


def test_phone_keypad_position_style_writes_the_key_and_a_superscript_position() -> None:
    artifact: Artifact = build("phone-keypad", {"style": "position", "plaintext": "Abc sz mill"}, make_context())
    assert ciphertext_of(artifact) == "2¹-2²-2³ / 7⁴-9⁴ / 6¹-4³-5³-5³"


def test_phone_keypad_rejects_digits_and_unknown_styles() -> None:
    error: MechanicBuildError = build_error("phone-keypad", {"plaintext": "Mill 12"}, make_context())
    assert error.message == "The plaintext 'MILL 12' has digits, which the phone keypad cannot encode."
    assert "style" in build_error("phone-keypad", {"style": "morse"}, make_context()).message


def test_phone_keypad_decodes_an_unknown_press_as_a_question_mark() -> None:
    artifact: Artifact = Artifact(html='<p class="mf-ciphertext">44-1 / 2222</p>', solver_text="")
    assert decode("phone-keypad", {}, make_context(), artifact) == "H? ?"


# nato-alphabet


def nato_entries(artifact: Artifact) -> list[str]:
    return [html.unescape(entry) for entry in re.findall(r'<li class="mf-nato-entry">([^<]*)</li>', artifact.html)]


def test_nato_spells_letters_and_digits_as_words() -> None:
    artifact: Artifact = build("nato-alphabet", {"plaintext": "Mill, 79"}, make_context())
    assert ciphertext_of(artifact) == "Mike India Lima Lima / Seven Nine"
    assert artifact.solver_text == "NATO alphabet: Mike India Lima Lima / Seven Nine"


def test_nato_scramble_numbers_each_letter_and_moves_every_word() -> None:
    artifact: Artifact = build("nato-alphabet", {"scramble": "true", "plaintext": "Old mill"}, make_context())
    entries: list[str] = nato_entries(artifact)
    assert sorted(entries, key=lambda entry: int(entry.split(".")[0])) == [
        "1. Oscar", "2. Lima", "3. Delta", "4. Mike", "5. India", "6. Lima", "7. Lima"
    ]  # fmt: skip
    assert all(not entry.startswith(f"{index}.") for index, entry in enumerate(entries, start=1))
    assert artifact.solver_text == "NATO words with their positions: " + "; ".join(entries)


def test_nato_scramble_order_depends_on_the_seed() -> None:
    params: dict[str, Any] = {"scramble": True, "plaintext": "Meet at the old mill"}
    first: list[str] = nato_entries(build("nato-alphabet", params, make_context(seed=1)))
    second: list[str] = nato_entries(build("nato-alphabet", params, make_context(seed=2)))
    assert first != second


def test_nato_decodes_unreadable_entries_as_question_marks() -> None:
    artifact: Artifact = Artifact(
        html='<li class="mf-nato-entry">2. Bogus</li><li class="mf-nato-entry">x Lima</li>', solver_text=""
    )
    assert decode("nato-alphabet", {"scramble": True}, make_context(), artifact) == "??"
    words: Artifact = Artifact(html='<p class="mf-ciphertext">Lima Bogus / Alfa</p>', solver_text="")
    assert decode("nato-alphabet", {}, make_context(), words) == "L? A"


# mirror-writing


def test_mirror_writing_keeps_the_original_text_in_a_mirrored_element() -> None:
    artifact: Artifact = build("mirror-writing", {"plaintext": "Meet at the Old Mill, señor"}, make_context())
    assert '<p class="mf-mirror">Meet at the Old Mill, señor</p>' in artifact.html
    assert artifact.solver_text == "Mirror-reversed text (it reads correctly in a mirror): roñes ,lliM dlO eht ta teeM"


def test_mirror_writing_escapes_markup_as_text() -> None:
    artifact: Artifact = build("mirror-writing", {"plaintext": "<b>Mill</b>"}, make_context())
    assert '<p class="mf-mirror">&lt;b&gt;Mill&lt;/b&gt;</p>' in artifact.html


# cryptogram


def test_cryptogram_substitutes_letters_consistently_and_never_with_themselves() -> None:
    plaintext: str = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG, MILL 7."
    artifact: Artifact = build("cryptogram", {"plaintext": plaintext, "revealed_letters": ["M", "I"]}, make_context())
    ciphertext: str = ciphertext_of(artifact)
    assert len(ciphertext) == len(plaintext)
    pairs: set[tuple[str, str]] = set(zip(plaintext, ciphertext, strict=True))
    letter_pairs: set[tuple[str, str]] = {(plain, cipher) for plain, cipher in pairs if plain.isalpha()}
    assert len(letter_pairs) == 26
    assert len({cipher for _, cipher in letter_pairs}) == 26
    assert all(plain != cipher for plain, cipher in letter_pairs)
    assert {(plain, cipher) for plain, cipher in pairs if not plain.isalpha()} == {
        (" ", " "), (",", ","), (".", "."), ("7", "7")
    }  # fmt: skip


def test_cryptogram_prints_the_revealed_letters_as_a_key() -> None:
    artifact: Artifact = build("cryptogram", {"plaintext": "Mill mill", "revealed_letters": ["í", "m"]}, make_context())
    ciphertext: str = ciphertext_of(artifact)
    key: str = f"{ciphertext[1]} = I, {ciphertext[0]} = M"
    assert f'<p class="mf-cipher-key">{key}</p>' in artifact.html
    assert artifact.solver_text == f"Ciphertext: {ciphertext}\nKnown letters: {key}"


def test_cryptogram_without_revealed_letters_prints_no_key() -> None:
    artifact: Artifact = build("cryptogram", {"plaintext": "Mill mill"}, make_context())
    assert "mf-cipher-key" not in artifact.html
    assert artifact.solver_text == f"Ciphertext: {ciphertext_of(artifact)}"


def test_cryptogram_alphabet_depends_on_the_seed() -> None:
    params: dict[str, Any] = {"plaintext": "Mill mill"}
    assert build("cryptogram", params, make_context(seed=1)) != build("cryptogram", params, make_context(seed=2))


def test_cryptogram_rejects_answer_letters_that_players_cannot_work_out() -> None:
    error: MechanicBuildError = build_error("cryptogram", {"plaintext": "Meet at the old mill"}, make_context())
    assert error.message == "These answer letters appear only once in the plaintext and are not revealed: I."
    assert "revealed_letters" in error.fix_hint


@pytest.mark.parametrize("letter", ["AB", "1", ""])
def test_cryptogram_rejects_a_revealed_letter_that_is_not_one_letter(letter: str) -> None:
    error: MechanicBuildError = build_error(
        "cryptogram", {"plaintext": "Mill mill", "revealed_letters": [letter]}, make_context()
    )
    assert error.message == f"The revealed letter '{letter}' is not one letter A-Z."
    assert "revealed_letters" in error.fix_hint
