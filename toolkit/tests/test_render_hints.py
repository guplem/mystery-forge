from test_render_support import golden_game

from mystery_forge.render.hints import CARDS_PER_SHEET, HintCardsPage, WarningContent, hint_sheets, puzzle_order_key


def test_the_hints_start_with_a_cover_without_hint_text() -> None:
    sheets = hint_sheets(golden_game())
    assert sheets[0].role == "warning"
    assert sheets[0].content == WarningContent(output="hints", title="The Lens of Gull Rock")


def test_each_puzzle_gets_its_hint_cards_and_an_answer_card_in_code_order() -> None:
    sheets = hint_sheets(golden_game())
    pages = [sheet.content for sheet in sheets[1:]]
    assert all(isinstance(page, HintCardsPage) for page in pages)
    cards = [card for page in pages if isinstance(page, HintCardsPage) for card in page.cards]
    assert [len(page.cards) for page in pages if isinstance(page, HintCardsPage)] == [CARDS_PER_SHEET, 5]
    assert [(card.code, card.label) for card in cards[:4]] == [
        ("A1", "Hint 1"),
        ("A1", "Hint 2"),
        ("A1", "Hint 3"),
        ("A1", "Answer"),
    ]
    assert cards[3].is_answer and cards[3].text == "boathouse"
    assert cards[0].text == "Look at the foot of the logbook page."
    assert [card.code for card in cards[-3:]] == ["B1", "B1", "B1"]


def test_puzzle_order_reads_the_number_as_a_number() -> None:
    puzzle = golden_game().puzzles[0]
    codes = ["B1", "A10", "A9"]
    ordered = sorted((puzzle.model_copy(update={"code": code}) for code in codes), key=puzzle_order_key)
    assert [item.code for item in ordered] == ["A9", "A10", "B1"]
