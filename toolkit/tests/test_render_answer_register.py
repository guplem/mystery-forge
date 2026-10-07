import re
from itertools import pairwise

from test_render_support import configured, golden_game

from mystery_forge.answers import normalize_answer
from mystery_forge.game import Game
from mystery_forge.render.answer_register import (
    AnswerRegister,
    build_answer_register,
    register_form,
    register_sort_key,
    same_shape,
)
from mystery_forge.spec.models import AnswerFormat, NearMiss, Stage

CORRECT_FORMS: set[str] = {"BOATHOUSE", "0726", "LOWTIDE", "THELOWTIDE", "ATLOWTIDE"}


def entry_texts(register: AnswerRegister) -> list[str]:
    return [entry.text for entry in register.entries]


def paragraph_for(register: AnswerRegister, text: str) -> str:
    number: int = next(entry.paragraph for entry in register.entries if entry.text == text)
    paragraph = next(paragraph for paragraph in register.paragraphs if paragraph.number == number)
    return f"{paragraph.outcome}|{paragraph.message}"


def with_puzzle(game: Game, index: int, **values: object) -> Game:
    puzzles = list(game.puzzles)
    puzzles[index] = puzzles[index].model_copy(update={"source": puzzles[index].source.model_copy(update=values)})
    return game.model_copy(update={"puzzles": puzzles})


def with_flow(game: Game, **values: object) -> Game:
    return game.model_copy(update={"flow": game.flow.model_copy(update=values)})


def neighbors(register: AnswerRegister, form: str) -> list[str]:
    return [text for text in entry_texts(register) if text != form and same_shape(form, text)]


def test_register_form_keeps_capital_letters_and_digits_only() -> None:
    assert register_form("Low-Tide, at the café!") == "LOWTIDEATTHECAFE"
    assert register_form("the boathouse") == "THEBOATHOUSE"
    assert register_form("07 26") == "0726"


def test_same_shape_compares_digit_counts_and_letter_counts() -> None:
    assert same_shape("0726", "1234")
    assert not same_shape("0726", "123")
    assert not same_shape("0726", "ABCD")
    assert same_shape("LOWTIDE", "ABCDE") and same_shape("LOWTIDE", "ABCDEFGHI")
    assert not same_shape("LOWTIDE", "ABCD") and not same_shape("LOWTIDE", "ABCDEFGHIJ")
    assert not same_shape("LOWTIDE", "1234567")


def test_every_entry_is_printed_in_one_normalized_form_and_only_once() -> None:
    texts = entry_texts(build_answer_register(golden_game()))
    assert all(re.fullmatch(r"[A-Z0-9]+", text) for text in texts)
    assert len(texts) == len(set(texts))
    assert set(texts) >= CORRECT_FORMS
    assert "YXLXQEORPB" in texts


def test_accepted_variants_with_the_same_form_share_one_entry() -> None:
    game = with_puzzle(golden_game(), 2, accepted=["Low-Tide", "LOW TIDE!", "the low tide"])
    register = build_answer_register(game)
    texts = entry_texts(register)
    assert texts.count("LOWTIDE") == 1
    assert "THELOWTIDE" in texts
    correct = [paragraph for paragraph in register.paragraphs if paragraph.outcome == "correct"]
    assert len(correct) == len({"BOATHOUSE", "0726", "LOWTIDE", "THELOWTIDE"})


def test_every_real_answer_hides_among_at_least_four_entries_of_the_same_shape() -> None:
    register = build_answer_register(golden_game())
    for form in CORRECT_FORMS:
        assert len(neighbors(register, form)) >= 4, form
    digit_entries = [text for text in entry_texts(register) if text.isdigit()]
    assert all(len(text) == 4 for text in digit_entries)


def test_word_decoys_come_from_the_document_texts() -> None:
    register = build_answer_register(golden_game())
    phrases: set[str] = set()
    for document in golden_game().documents:
        for line in document.text.splitlines():
            words: list[str] = [register_form(word) for word in line.split()]
            phrases.update(words)
            phrases.update(first + second for first, second in pairwise(words))
    known: set[str] = CORRECT_FORMS | {"YXLXQEORPB"}
    from_documents = [text for text in entry_texts(register) if text not in known and not text.isdigit()]
    assert from_documents
    assert set(from_documents) <= phrases


def test_a_puzzle_decoy_joins_the_register_but_never_replaces_a_correct_entry() -> None:
    game = with_puzzle(golden_game(), 0, decoys=["Lamp room", "the boathouse"])
    register = build_answer_register(game)
    assert "LAMPROOM" in entry_texts(register)
    assert "THEBOATHOUSE" not in entry_texts(register)
    assert paragraph_for(register, "LAMPROOM") == "wrong|Nothing happens. Try again."


def test_a_long_answer_takes_what_the_documents_offer() -> None:
    game = with_puzzle(golden_game(), 2, answer="the longest answer that no document can match at all", accepted=[])
    register = build_answer_register(game)
    assert neighbors(register, "LONGESTANSWERTHATNODOCUMENTCANMATCHATALL") == []


def test_a_one_digit_answer_gets_one_digit_codes() -> None:
    game = with_puzzle(golden_game(), 1, answer="7")
    register = build_answer_register(game)
    assert len(neighbors(register, "7")) >= 4


def test_every_entry_has_its_own_paragraph_with_a_stable_number() -> None:
    register = build_answer_register(golden_game())
    numbers = [entry.paragraph for entry in register.entries]
    assert len(set(numbers)) == len(numbers) == len(register.paragraphs)
    assert all(100 <= number <= 999 for number in numbers)
    assert [paragraph.number for paragraph in register.paragraphs] == sorted(numbers)
    assert build_answer_register(golden_game()) == register
    other_seed = golden_game().model_copy(update={"brief": golden_game().brief.model_copy(update={"seed": 7})})
    assert [entry.paragraph for entry in build_answer_register(other_seed).entries] != numbers


def test_a_correct_paragraph_says_only_what_to_do_next() -> None:
    register = build_answer_register(golden_game())
    assert paragraph_for(register, "BOATHOUSE") == "correct|Correct! Open Envelope B now."
    assert paragraph_for(register, "0726") == "correct|Correct! Write it in your notes."
    assert paragraph_for(register, "LOWTIDE") == "correct|Correct! This was the last puzzle: turn to the accusation."
    assert paragraph_for(register, "YXLXQEORPB") == (
        "near_miss|You moved the letters the wrong way. Count back, not forward."
    )
    decoy = next(text for text in entry_texts(register) if text.isdigit() and text != "0726")
    assert paragraph_for(register, decoy) == "wrong|Nothing happens. Try again."


def test_a_correct_paragraph_never_shows_a_code_a_title_or_story_text() -> None:
    game = golden_game()
    messages: list[str] = [
        paragraph.message for paragraph in build_answer_register(game).paragraphs if paragraph.outcome == "correct"
    ]
    for puzzle in game.puzzles:
        for message in messages:
            assert puzzle.code not in message
            assert puzzle.source.title not in message
            assert puzzle.source.reveals not in message


def test_an_answer_that_a_later_puzzle_needs_must_be_written_down() -> None:
    stages = [Stage(id="A", label="Desk", opens_with="start"), Stage(id="B", label="Box", opens_with="P2")]
    register = build_answer_register(with_flow(golden_game(), stages=stages))
    assert paragraph_for(register, "BOATHOUSE") == "correct|Correct! Write this answer down: a later puzzle needs it."
    assert paragraph_for(register, "0726") == "correct|Correct! Open Envelope B now."


def test_the_final_puzzle_without_an_accusation_goes_to_the_notes() -> None:
    register = build_answer_register(with_flow(golden_game(), accusation=False))
    assert paragraph_for(register, "LOWTIDE") == "correct|Correct! Write it in your notes."


def test_name_answers_get_the_other_character_names_as_decoys() -> None:
    game = with_puzzle(golden_game(), 0, answer="Felix Ward", answer_format=AnswerFormat(kind="name", label="a name"))
    texts = entry_texts(build_answer_register(game))
    assert {"FELIXWARD", "ANARUIZ", "MAUDPRICE", "TOMBELL"} <= set(texts)


def test_name_decoys_that_contain_the_answer_are_left_out() -> None:
    game = with_puzzle(golden_game(), 0, answer="Ward", answer_format=AnswerFormat(kind="name", label="a surname"))
    assert "FELIXWARD" not in entry_texts(build_answer_register(game))


def test_the_register_speaks_the_game_language() -> None:
    game = configured(golden_game(), {"language": "es"})
    assert paragraph_for(build_answer_register(game), "BOATHOUSE").startswith("correct|¡Correcto!")


def test_a_spanish_answer_with_an_article_is_listed_with_and_without_it() -> None:
    game = with_puzzle(configured(golden_game(), {"language": "es"}), 0, answer="el faro")
    texts = entry_texts(build_answer_register(game))
    assert {"ELFARO", "FARO"} <= set(texts)
    assert normalize_answer("ELFARO", "es") == "elfaro"


def test_register_sort_key_puts_numbers_first_and_ignores_accents() -> None:
    assert sorted(["ÉCOLE", "ZOO", "10", "9", "ABC"], key=register_sort_key) == ["9", "10", "ABC", "ÉCOLE", "ZOO"]


def test_a_near_miss_that_looks_like_a_real_answer_stays_off_the_paper_register() -> None:
    """Live game 5 printed EILSER ("Close.") right next to the answer EISLER, which gave the answer away."""
    near_misses = [
        NearMiss(answer="boathuose", message="Close."),
        NearMiss(answer="botahouse", message="Close."),
        NearMiss(answer="yxlxqeorpb", message="Count back."),
    ]
    texts = entry_texts(build_answer_register(with_puzzle(golden_game(), 0, near_misses=near_misses)))
    assert "BOATHUOSE" not in texts
    assert "BOTAHOUSE" not in texts
    assert "YXLXQEORPB" in texts
