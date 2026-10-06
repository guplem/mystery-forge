from test_checks_support import golden_game

from mystery_forge.checks.game_index import clues_by_id, mentions, puzzles_in_code_order, squash


def test_squash_keeps_only_letters_and_digits_and_every_word() -> None:
    assert squash("The B O A T, nº 7!") == "theboatno7"


def test_mentions_searches_long_answers_inside_text_and_short_ones_as_words() -> None:
    assert mentions("Look in the Boat-House.", "boathouse")
    assert mentions("Dial 07 now", "07")
    assert not mentions("Dial 3074 now", "07")
    assert not mentions("Anything at all", "")


def test_the_clue_index_and_the_code_order() -> None:
    assert clues_by_id(golden_game())["wet-boots"].file == "story.yaml"
    assert clues_by_id(golden_game())["tide-table"].puzzle is not None
    assert [puzzle.code for puzzle in puzzles_in_code_order(golden_game())] == ["A1", "A2", "B1"]
