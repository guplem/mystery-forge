import random

import pytest

from mystery_forge.mechanics.base import MechanicBuildError, MechanicContext
from mystery_forge.mechanics.text_tools import (
    attribute_values,
    cyclic_permutation,
    escape_text,
    fold_text,
    letters_only,
    marked_texts,
    plaintext_for,
    require_no_digits,
)


def make_context(answer: str, language: str = "en") -> MechanicContext:
    return MechanicContext(puzzle_id="P1", answer=answer, language=language, seed=7, documents={})


def test_fold_text_removes_accents_uppercases_and_keeps_word_spaces() -> None:
    assert fold_text("  Mañana  en el Faro ", keep_punctuation=False) == "MANANA EN EL FARO"


def test_fold_text_transliterates_special_letters_and_drops_other_symbols() -> None:
    assert fold_text("Æsir straße <b>", keep_punctuation=False) == "AESIR STRASSE B"


def test_fold_text_keeps_basic_punctuation_only_when_asked() -> None:
    assert fold_text("Meet at 9, the mill!", keep_punctuation=True) == "MEET AT 9, THE MILL!"
    assert fold_text("Meet at 9, the mill!", keep_punctuation=False) == "MEET AT 9 THE MILL"


def test_letters_only_keeps_a_to_z() -> None:
    assert letters_only("Old mill, 1920!") == "OLDMILL"


def test_plaintext_for_defaults_to_the_answer() -> None:
    assert plaintext_for(None, make_context("El Faro", "es"), keep_punctuation=False) == "EL FARO"


def test_plaintext_for_accepts_a_message_that_contains_the_answer() -> None:
    context: MechanicContext = make_context("The Mill")
    assert plaintext_for("Meet at the old mill.", context, keep_punctuation=True) == "MEET AT THE OLD MILL."


def test_plaintext_for_rejects_a_message_without_the_answer() -> None:
    with pytest.raises(MechanicBuildError) as raised:
        plaintext_for("Meet at the bridge", make_context("mill"), keep_punctuation=False)
    assert raised.value.message == "The plaintext 'MEET AT THE BRIDGE' does not contain the answer 'mill'."
    assert "plaintext" in raised.value.fix_hint


def test_plaintext_for_rejects_an_answer_without_letters_or_digits() -> None:
    with pytest.raises(MechanicBuildError) as raised:
        plaintext_for(None, make_context("?!"), keep_punctuation=False)
    assert raised.value.message == "The answer '?!' has no letters or digits to encode."
    assert "answer" in raised.value.fix_hint


def test_require_no_digits_accepts_letters_and_rejects_digits() -> None:
    require_no_digits("OLD MILL", "Braille")
    with pytest.raises(MechanicBuildError) as raised:
        require_no_digits("ROOM 12", "Braille")
    assert raised.value.message == "The plaintext 'ROOM 12' has digits, which Braille cannot encode."
    assert "words" in raised.value.fix_hint


def test_escape_text_escapes_markup() -> None:
    assert escape_text('<b>&"x"') == "&lt;b&gt;&amp;&#34;x&#34;"


def test_marked_texts_returns_the_text_of_each_marked_element_in_order() -> None:
    html: str = (
        '<div><p class="mf-note">skip</p><p class="mf-a mf-ciphertext">A&amp;B</p><p class="mf-ciphertext">C</p></div>'
    )
    assert marked_texts(html, "mf-ciphertext") == ["A&B", "C"]


def test_marked_texts_ignores_elements_without_a_class_value() -> None:
    assert marked_texts("<p class>x</p><span>y</span>", "mf-ciphertext") == []


def test_attribute_values_returns_values_in_document_order() -> None:
    html: str = '<svg data-symbol="A"></svg><span data-symbol=" "></span><svg data-symbol="B"/><i data-other="x"></i>'
    assert attribute_values(html, "data-symbol") == ["A", " ", "B"]


@pytest.mark.parametrize("seed", range(20))
def test_cyclic_permutation_moves_every_item_and_depends_only_on_the_seed(seed: int) -> None:
    order: list[int] = cyclic_permutation(9, random.Random(seed))
    assert sorted(order) == list(range(9))
    assert all(order[index] != index for index in range(9))
    assert order == cyclic_permutation(9, random.Random(seed))


def test_cyclic_permutation_of_one_item_is_that_item() -> None:
    assert cyclic_permutation(1, random.Random(1)) == [0]
