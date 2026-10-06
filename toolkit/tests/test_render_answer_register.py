from test_render_support import configured, golden_game

from mystery_forge.game import Game
from mystery_forge.render.answer_register import (
    AnswerRegister,
    build_answer_register,
    register_sort_key,
)
from mystery_forge.spec.models import AnswerFormat


def entry_texts(register: AnswerRegister) -> list[str]:
    return [entry.text for entry in register.entries]


def paragraph_for(register: AnswerRegister, text: str) -> str:
    number: int = next(entry.paragraph for entry in register.entries if entry.text == text)
    paragraph = next(paragraph for paragraph in register.paragraphs if paragraph.number == number)
    return f"{paragraph.outcome}|{paragraph.message}|{paragraph.action}|{paragraph.reveals}"


def with_puzzle(game: Game, index: int, **values: object) -> Game:
    puzzles = list(game.puzzles)
    puzzles[index] = puzzles[index].model_copy(update={"source": puzzles[index].source.model_copy(update=values)})
    return game.model_copy(update={"puzzles": puzzles})


def test_the_register_lists_answers_variants_near_misses_and_digit_decoys_in_order() -> None:
    register = build_answer_register(golden_game())
    texts = entry_texts(register)
    assert {"BOATHOUSE", "0726", "LOW TIDE", "THE LOW TIDE", "AT LOW TIDE", "YXLXQEORPB"} <= set(texts)
    digit_entries = [text for text in texts if text.isdigit()]
    assert len(digit_entries) == 4
    assert all(len(text) == 4 for text in digit_entries)
    assert digit_entries == sorted(digit_entries, key=int)
    assert texts[: len(digit_entries)] == digit_entries
    words = texts[len(digit_entries) :]
    assert words == sorted(words)


def test_every_entry_has_its_own_paragraph_with_a_stable_number() -> None:
    register = build_answer_register(golden_game())
    numbers = [entry.paragraph for entry in register.entries]
    assert len(set(numbers)) == len(numbers) == len(register.paragraphs)
    assert all(100 <= number <= 999 for number in numbers)
    assert [paragraph.number for paragraph in register.paragraphs] == sorted(numbers)
    assert build_answer_register(golden_game()) == register
    other_seed = golden_game().model_copy(update={"brief": golden_game().brief.model_copy(update={"seed": 7})})
    assert [entry.paragraph for entry in build_answer_register(other_seed).entries] != numbers


def test_the_results_say_what_to_do_next() -> None:
    register = build_answer_register(golden_game())
    assert paragraph_for(register, "BOATHOUSE") == (
        "correct|Correct! You solved puzzle A1.|Open Envelope B now.|Tom hid the spare keys in the boathouse."
    )
    assert paragraph_for(register, "0726").startswith("correct|Correct! You solved puzzle A2.|Keep this answer")
    assert "accusation form" in paragraph_for(register, "AT LOW TIDE")
    assert paragraph_for(register, "YXLXQEORPB") == (
        "near_miss|You moved the letters the wrong way. Count back, not forward.||"
    )
    decoy = next(text for text in entry_texts(register) if text.isdigit() and text != "0726")
    assert paragraph_for(register, decoy) == "wrong|Nothing happens. Try again.||"


def test_the_final_puzzle_without_an_accusation_closes_the_case() -> None:
    game = golden_game()
    game = game.model_copy(update={"flow": game.flow.model_copy(update={"accusation": False})})
    assert "You solved the case" in paragraph_for(build_answer_register(game), "LOW TIDE")


def test_decoys_join_the_register_but_never_replace_a_correct_entry() -> None:
    game = with_puzzle(golden_game(), 0, decoys=["Lamp room", "the boathouse"])
    register = build_answer_register(game)
    assert "LAMP ROOM" in entry_texts(register)
    assert "THE BOATHOUSE" not in entry_texts(register)
    assert paragraph_for(register, "LAMP ROOM") == "wrong|Nothing happens. Try again.||"


def test_name_answers_get_the_other_character_names_as_decoys() -> None:
    game = with_puzzle(golden_game(), 0, answer="Felix Ward", answer_format=AnswerFormat(kind="name", label="a name"))
    texts = entry_texts(build_answer_register(game))
    assert {"FELIX WARD", "ANA RUIZ", "MAUD PRICE", "TOM BELL"} <= set(texts)


def test_name_decoys_that_contain_the_answer_are_left_out() -> None:
    game = with_puzzle(golden_game(), 0, answer="Ward", answer_format=AnswerFormat(kind="name", label="a surname"))
    assert "FELIX WARD" not in entry_texts(build_answer_register(game))


def test_the_register_speaks_the_game_language() -> None:
    game = configured(golden_game(), {"language": "es"})
    assert paragraph_for(build_answer_register(game), "BOATHOUSE").startswith("correct|¡Correcto!")


def test_register_sort_key_puts_numbers_first_and_ignores_accents() -> None:
    assert sorted(["ÉCOLE", "ZOO", "10", "9", "ABC"], key=register_sort_key) == ["9", "10", "ABC", "ÉCOLE", "ZOO"]
