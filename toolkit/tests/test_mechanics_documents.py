import html
import re
from typing import Any

import pytest

from mystery_forge.answers import normalize_answer
from mystery_forge.mechanics import documents, registry
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
    parse_params,
)

LETTER_DOCUMENT: str = "Fog rolled over the old harbor.\n\nA ring of keys lay on the table.\nOnly Otto knew the code."


def make_context(answer: str, documents_by_id: dict[str, str] | None = None, seed: int = 5) -> MechanicContext:
    return MechanicContext(
        puzzle_id="P1",
        answer=answer,
        language="en",
        seed=seed,
        documents=documents_by_id if documents_by_id is not None else {"letter": LETTER_DOCUMENT},
    )


def implementation(mechanic_id: str) -> MechanicImplementation[Any]:
    return registry.all_implementations()[mechanic_id]


def build(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> Artifact:
    chosen: MechanicImplementation[Any] = implementation(mechanic_id)
    return chosen.build(parse_params(chosen, raw_params), context)


def rendered_from(artifact: Artifact) -> RenderedArtifact:
    return RenderedArtifact(text=html.unescape(re.sub(r"<[^>]+>", "", artifact.html)), html=artifact.html)


def decode(mechanic_id: str, raw_params: dict[str, Any], artifact: Artifact, context: MechanicContext) -> str:
    chosen: MechanicImplementation[Any] = implementation(mechanic_id)
    assert chosen.decode_rendered is not None
    return chosen.decode_rendered(rendered_from(artifact), parse_params(chosen, raw_params), context)


def expect_build_error(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> MechanicBuildError:
    with pytest.raises(MechanicBuildError) as raised:
        build(mechanic_id, raw_params, context)
    return raised.value


@pytest.mark.parametrize("mechanic_id", ["book-cipher", "cut-strips", "timeline-order"])
def test_document_mechanics_are_registered(mechanic_id: str) -> None:
    assert implementation(mechanic_id) in documents.IMPLEMENTATIONS


# book-cipher


def test_book_cipher_letter_references_point_to_words_that_start_with_the_answer_letters() -> None:
    params: dict[str, Any] = {"document": "letter", "unit": "letter", "reference_style": "line.word"}
    artifact: Artifact = build("book-cipher", params, make_context("fork"))
    references: list[str] = artifact.solver_text.split()
    lines: list[list[str]] = [line.split() for line in LETTER_DOCUMENT.splitlines() if line.strip()]
    first_letters: str = ""
    for reference in references:
        line_number, word_number = (int(part) for part in reference.split("."))
        first_letters += lines[line_number - 1][word_number - 1][0].lower()
    assert first_letters == "fork"
    assert 'class="mf-book-cipher"' in artifact.html
    assert artifact.print_notes == ()


def test_book_cipher_word_references_use_global_word_numbers_and_fold_accents() -> None:
    document: str = "El código está bajo el faro.\nNadie mira el faro."
    params: dict[str, Any] = {"document": "nota", "unit": "word", "reference_style": "word"}
    context: MechanicContext = make_context("Código faro", {"nota": document})
    artifact: Artifact = build("book-cipher", params, context)
    words: list[str] = document.split()
    picked: list[str] = [normalize_answer(words[int(reference) - 1], "") for reference in artifact.solver_text.split()]
    assert picked == ["codigo", "faro"]
    assert decode("book-cipher", params, artifact, context) == "codigo faro"


def test_book_cipher_prefers_unused_occurrences_for_repeated_letters() -> None:
    params: dict[str, Any] = {"document": "letter", "unit": "letter", "reference_style": "word"}
    artifact: Artifact = build("book-cipher", params, make_context("too"))
    references: list[str] = artifact.solver_text.split()
    assert len(set(references)) == 3


def test_book_cipher_reuses_an_occurrence_when_the_document_has_only_one() -> None:
    params: dict[str, Any] = {"document": "note", "unit": "letter", "reference_style": "word"}
    artifact: Artifact = build("book-cipher", params, make_context("aa", {"note": "apple pie"}))
    assert artifact.solver_text.split() == ["1", "1"]


def test_book_cipher_is_deterministic_and_depends_on_the_seed() -> None:
    params: dict[str, Any] = {"document": "letter", "unit": "letter"}
    first: Artifact = build("book-cipher", params, make_context("too", seed=1))
    again: Artifact = build("book-cipher", params, make_context("too", seed=1))
    assert first == again
    variants: set[str] = {build("book-cipher", params, make_context("too", seed=seed)).html for seed in range(10)}
    assert len(variants) > 1


@pytest.mark.parametrize(("unit", "style"), [("letter", "line.word"), ("letter", "word"), ("word", "line.word")])
def test_book_cipher_round_trip(unit: str, style: str) -> None:
    params: dict[str, Any] = {"document": "letter", "unit": unit, "reference_style": style}
    answer: str = "the code" if unit == "word" else "Rook"
    context: MechanicContext = make_context(answer)
    artifact: Artifact = build("book-cipher", params, context)
    assert normalize_answer(decode("book-cipher", params, artifact, context), "en") == context.normalized_answer


def test_book_cipher_decode_reads_the_rendered_document_text_from_the_context() -> None:
    params: dict[str, Any] = {"document": "letter", "unit": "letter", "reference_style": "word"}
    context: MechanicContext = make_context("fork")
    artifact: Artifact = build("book-cipher", params, context)
    changed: MechanicContext = make_context("fork", {"letter": "Zebra " * 40})
    assert decode("book-cipher", params, artifact, changed) == "z" * 4


def test_book_cipher_decode_skips_references_outside_the_document() -> None:
    params: dict[str, Any] = {"document": "letter", "unit": "letter", "reference_style": "line.word"}
    context: MechanicContext = make_context("fork")
    artifact: Artifact = build("book-cipher", params, context)
    shortened: MechanicContext = make_context("fork", {"letter": "Fog"})
    decoded: str = decode("book-cipher", params, artifact, shortened)
    assert len(decoded) < 4


def test_book_cipher_decode_reports_a_missing_document() -> None:
    params: dict[str, Any] = {"document": "letter", "unit": "letter"}
    artifact: Artifact = build("book-cipher", params, make_context("fork"))
    with pytest.raises(MechanicBuildError) as raised:
        decode("book-cipher", params, artifact, make_context("fork", {}))
    assert "letter" in raised.value.message


def test_book_cipher_rejects_a_missing_document() -> None:
    error: MechanicBuildError = expect_build_error("book-cipher", {"document": "diary"}, make_context("fork"))
    assert error.message == "The document 'diary' does not exist."
    assert "letter" in error.fix_hint


def test_book_cipher_rejects_a_letter_that_no_word_starts_with() -> None:
    error: MechanicBuildError = expect_build_error("book-cipher", {"document": "letter"}, make_context("zebra"))
    assert error.message == "No word in the document 'letter' starts with 'z'."
    assert error.fix_hint == "Add a word that starts with 'z' to the document, or use another document."


def test_book_cipher_rejects_an_answer_word_that_is_not_in_the_document() -> None:
    error: MechanicBuildError = expect_build_error(
        "book-cipher", {"document": "letter", "unit": "word"}, make_context("lighthouse")
    )
    assert error.message == "The document 'letter' does not contain the word 'lighthouse'."
    assert error.fix_hint == "Add the word 'lighthouse' to the document, or use the unit 'letter'."


@pytest.mark.parametrize("unit", ["letter", "word"])
def test_book_cipher_rejects_an_answer_without_letters(unit: str) -> None:
    error: MechanicBuildError = expect_build_error(
        "book-cipher", {"document": "letter", "unit": unit}, make_context("?!")
    )
    assert error.message == "The answer has no letters or digits."
    assert error.fix_hint


def test_book_cipher_escapes_the_references() -> None:
    artifact: Artifact = build("book-cipher", {"document": "letter"}, make_context("fork"))
    assert "<script" not in artifact.html


# cut-strips

MESSAGE: str = "The spare key hides under the old lighthouse stairs"


def strip_blocks(artifact: Artifact) -> list[str]:
    return re.findall(r'<div class="mf-strip"[^>]*>(.*?)</div>', artifact.html, flags=re.DOTALL)


def test_cut_strips_vertical_strips_reassemble_the_message_by_dot_count() -> None:
    params: dict[str, Any] = {"message": MESSAGE, "strips": "5", "rows": "3"}
    artifact: Artifact = build("cut-strips", params, make_context("lighthouse"))
    blocks: list[str] = strip_blocks(artifact)
    assert len(blocks) == 5
    ordered: list[tuple[int, list[str]]] = sorted(
        (block.count("•"), [html.unescape(line) for line in re.findall(r'"mf-strip-line">(.*?)</span>', block)])
        for block in blocks
    )
    assert [dots for dots, _lines in ordered] == [1, 2, 3, 4, 5]
    row_count: int = len(ordered[0][1])
    text: str = "".join("".join(lines[row] for _dots, lines in ordered) for row in range(row_count))
    assert text.replace("\u00a0", " ").strip() == MESSAGE
    assert artifact.print_notes == ("When you open this envelope, cut the strips apart along the dashed lines.",)


def test_cut_strips_say_when_to_cut_in_the_game_language() -> None:
    context: MechanicContext = make_context("lighthouse").model_copy(update={"language": "es"})
    artifact: Artifact = build("cut-strips", {"message": MESSAGE}, context)
    assert artifact.print_notes == ("Cuando abras este sobre, separa las tiras: recorta por las líneas discontinuas.",)


def test_cut_strips_horizontal_strips_hold_one_line_each() -> None:
    params: dict[str, Any] = {"message": MESSAGE, "strips": 4, "orientation": "horizontal"}
    artifact: Artifact = build("cut-strips", params, make_context("lighthouse"))
    blocks: list[str] = strip_blocks(artifact)
    assert len(blocks) == 4
    for block in blocks:
        assert len(re.findall(r'"mf-strip-line"', block)) == 1


def test_cut_strips_shows_the_strips_out_of_order_with_distinct_symbols() -> None:
    for seed in range(20):
        artifact: Artifact = build("cut-strips", {"message": "abcdef", "strips": 2}, make_context("abc", seed=seed))
        dots: list[int] = [block.count("•") for block in strip_blocks(artifact)]
        assert dots == [2, 1]
    artifact = build("cut-strips", {"message": MESSAGE, "strips": 12}, make_context("key"))
    symbols: list[str] = re.findall(r'data-symbol="([^"]+)"', artifact.html)
    assert len(set(symbols)) == 12
    assert "Strip" in artifact.solver_text


def test_cut_strips_is_deterministic() -> None:
    params: dict[str, Any] = {"message": MESSAGE}
    assert build("cut-strips", params, make_context("key", seed=9)) == build(
        "cut-strips", params, make_context("key", seed=9)
    )


@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
def test_cut_strips_round_trip(orientation: str) -> None:
    params: dict[str, Any] = {"message": MESSAGE, "orientation": orientation}
    context: MechanicContext = make_context("Lighthouse")
    artifact: Artifact = build("cut-strips", params, context)
    assert normalize_answer(decode("cut-strips", params, artifact, context), "en") == "lighthouse"


def test_cut_strips_decode_returns_the_message_when_the_answer_is_lost() -> None:
    params: dict[str, Any] = {"message": MESSAGE, "orientation": "horizontal"}
    artifact: Artifact = build("cut-strips", params, make_context("Lighthouse"))
    decoded: str = decode("cut-strips", params, artifact, make_context("cellar"))
    assert normalize_answer(decoded, "") == normalize_answer(MESSAGE, "")


def test_cut_strips_rejects_a_message_without_the_answer() -> None:
    error: MechanicBuildError = expect_build_error("cut-strips", {"message": MESSAGE}, make_context("cellar"))
    assert error.message == "The message does not contain the answer 'cellar'."
    assert error.fix_hint == "Write the answer inside the message."


def test_cut_strips_rejects_a_message_shorter_than_the_strip_count() -> None:
    error: MechanicBuildError = expect_build_error("cut-strips", {"message": "key", "strips": 4}, make_context("key"))
    assert error.message == "The message has 3 characters, fewer than the 4 strips."
    assert error.fix_hint == "Write a longer message or use fewer strips."


def test_cut_strips_rejects_an_answer_without_letters() -> None:
    error: MechanicBuildError = expect_build_error("cut-strips", {"message": MESSAGE}, make_context("..."))
    assert error.message == "The answer has no letters or digits."


def test_cut_strips_escapes_the_message() -> None:
    artifact: Artifact = build("cut-strips", {"message": "<script>x</script> key"}, make_context("key"))
    assert "<script" not in artifact.html


def test_cut_strips_rejects_a_strip_count_out_of_range() -> None:
    with pytest.raises(MechanicBuildError):
        parse_params(implementation("cut-strips"), {"message": MESSAGE, "strips": "1"})


# timeline-order

EVENTS: list[dict[str, str]] = [
    {"when": "1923-05-02 21:15", "text": "Omar leaves the club."},
    {"when": "1923-05-02 20:40", "text": "The lights go out."},
    {"when": "1923-05-03 08:00", "text": "Elena finds the body."},
    {"when": "1923-05-02 22:05", "text": "Á shot is heard."},
]


def test_timeline_order_cards_in_date_order_spell_the_answer() -> None:
    artifact: Artifact = build("timeline-order", {"events": EVENTS}, make_context("Toae"))
    cards: list[tuple[str, str]] = re.findall(
        r'data-when="([^"]+)">.*?"mf-timeline-text">(.*?)</p>', artifact.html, flags=re.DOTALL
    )
    assert len(cards) == 4
    assert "".join(normalize_answer(text, "")[0] for _when, text in sorted(cards)) == "toae"
    assert [when for when, _text in cards] != sorted(when for when, _text in cards)
    assert "1923-05-02 21:15" in artifact.solver_text


def test_timeline_order_never_shows_the_cards_already_sorted() -> None:
    events: list[dict[str, str]] = EVENTS[:2]
    for seed in range(20):
        artifact: Artifact = build("timeline-order", {"events": events}, make_context("TO", seed=seed))
        whens: list[str] = re.findall(r'data-when="([^"]+)"', artifact.html)
        assert whens == ["1923-05-02 21:15", "1923-05-02 20:40"]


def test_timeline_order_is_deterministic() -> None:
    assert build("timeline-order", {"events": EVENTS}, make_context("toae", seed=2)) == build(
        "timeline-order", {"events": EVENTS}, make_context("toae", seed=2)
    )


def test_timeline_order_round_trip() -> None:
    context: MechanicContext = make_context("TOAE")
    artifact: Artifact = build("timeline-order", {"events": EVENTS}, context)
    assert decode("timeline-order", {"events": EVENTS}, artifact, context) == "toae"


def test_timeline_order_rejects_an_unparsable_date() -> None:
    events: list[dict[str, str]] = [*EVENTS[:3], {"when": "May 2nd", "text": "Echo"}]
    error: MechanicBuildError = expect_build_error("timeline-order", {"events": events}, make_context("toee"))
    assert error.message == "The event 'Echo' has the date 'May 2nd', which is not in the form YYYY-MM-DD HH:MM."
    assert error.fix_hint == "Write the date as YYYY-MM-DD HH:MM, for example 1923-05-02 21:15."


def test_timeline_order_rejects_two_events_at_the_same_time() -> None:
    events: list[dict[str, str]] = [*EVENTS[:3], {"when": "1923-05-02 21:15", "text": "Echo"}]
    error: MechanicBuildError = expect_build_error("timeline-order", {"events": events}, make_context("toee"))
    assert error.message == "Two events happen at 1923-05-02 21:15."
    assert error.fix_hint == "Give every event a different date and time."


def test_timeline_order_rejects_an_event_text_without_letters() -> None:
    events: list[dict[str, str]] = [*EVENTS[:3], {"when": "1923-05-04 10:00", "text": "..."}]
    error: MechanicBuildError = expect_build_error("timeline-order", {"events": events}, make_context("toe"))
    assert error.message == "The event at 1923-05-04 10:00 has no letters."
    assert error.fix_hint


def test_timeline_order_rejects_first_letters_that_do_not_spell_the_answer() -> None:
    error: MechanicBuildError = expect_build_error("timeline-order", {"events": EVENTS}, make_context("tree"))
    assert error.message == "In date order, the first letters spell 'toae', not the answer 'tree'."
    assert error.fix_hint == "Change the event texts or dates so that the first letters spell the answer."


def test_timeline_order_escapes_the_event_text() -> None:
    events: list[dict[str, str]] = [
        {"when": "2000-01-01 10:00", "text": "<script>alert(1)</script>"},
        {"when": "2000-01-01 11:00", "text": "Bye"},
    ]
    artifact: Artifact = build("timeline-order", {"events": events}, make_context("sb"))
    assert "<script" not in artifact.html
