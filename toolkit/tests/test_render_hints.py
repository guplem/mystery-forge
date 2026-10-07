from test_render_support import golden_game

from mystery_forge.game import Game
from mystery_forge.render.hints import (
    CARD_LAYOUTS,
    HINTS_GROUP,
    HintCardsPage,
    WarningContent,
    card_capacity,
    card_layout,
    hint_sheets,
    puzzle_order_key,
)
from mystery_forge.spec.models import Hint


def card_pages(game: Game, levels: dict[str, int] | None = None) -> list[HintCardsPage]:
    pages = [sheet.content for sheet in hint_sheets(game, levels)[1:]]
    assert all(isinstance(page, HintCardsPage) for page in pages)
    return pages  # type: ignore[return-value]


def with_hint_text(game: Game, hint_text: str) -> Game:
    puzzles = list(game.puzzles)
    source = puzzles[0].source
    hints = [Hint(level=1, text=hint_text), *source.hints[1:]]
    puzzles[0] = puzzles[0].model_copy(update={"source": source.model_copy(update={"hints": hints})})
    return game.model_copy(update={"puzzles": puzzles})


def test_the_hints_start_with_a_cover_without_hint_text() -> None:
    sheets = hint_sheets(golden_game())
    assert sheets[0].role == "warning"
    assert sheets[0].content == WarningContent(output="hints", title="The Lens of Gull Rock")
    assert sheets[0].group is None
    assert {sheet.group for sheet in sheets[1:]} == {HINTS_GROUP}


def test_each_puzzle_gets_its_hint_cards_and_an_answer_card_in_code_order() -> None:
    pages = card_pages(golden_game())
    cards = [card for page in pages for card in page.cards]
    assert [(len(page.cards), page.columns, page.rows) for page in pages] == [(6, 2, 3), (5, 2, 3)]
    assert [(card.code, card.label) for card in cards[:4]] == [
        ("A1", "Hint 1"),
        ("A1", "Hint 2"),
        ("A1", "Hint 3"),
        ("A1", "Answer"),
    ]
    assert cards[3].is_answer and cards[3].text == "boathouse"
    assert cards[0].text == "Look at the foot of the logbook page."
    assert [card.code for card in cards[-3:]] == ["B1", "B1", "B1"]


def test_a_long_hint_gets_bigger_cards_and_so_does_a_tighter_level() -> None:
    long_game = with_hint_text(golden_game(), "Look closely. " * 30)

    def first_grid(game: Game, levels: dict[str, int] | None = None) -> tuple[int, int]:
        page = card_pages(game, levels)[0]
        return (page.columns, page.rows)

    assert first_grid(long_game) == (2, 2)
    assert first_grid(golden_game(), {HINTS_GROUP: 2}) == (2, 1)
    assert first_grid(golden_game(), {HINTS_GROUP: 9}) == (1, 1)


def test_card_layout_picks_the_smallest_grid_that_holds_the_text() -> None:
    assert card_layout("A4", 10, 0) == CARD_LAYOUTS[0]
    assert card_layout("A4", card_capacity("A4", 2, 3) + 1, 0) == CARD_LAYOUTS[1]
    assert card_layout("Letter", 100_000, 0) == CARD_LAYOUTS[-1]
    assert card_capacity("Letter", 2, 3) < card_capacity("A4", 2, 3) < card_capacity("A4", 2, 2)


def test_puzzle_order_reads_the_number_as_a_number() -> None:
    puzzle = golden_game().puzzles[0]
    codes = ["B1", "A10", "A9"]
    ordered = sorted((puzzle.model_copy(update={"code": code}) for code in codes), key=puzzle_order_key)
    assert [item.code for item in ordered] == ["A9", "A10", "B1"]
