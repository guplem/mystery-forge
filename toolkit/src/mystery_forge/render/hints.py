"""The sheet plan of the hints: a cover with no spoilers, then fold cards on a cut grid.

Each card has an outside half (puzzle code, puzzle title, "Hint 1") and an inside half with the text, printed
upside down over a hatch band. Players fold the card so the text is hidden until they turn it over.
The first page carries no hint text, so a file thumbnail or a quick look does not spoil anything.
"""

from dataclasses import dataclass
from typing import Final

from mystery_forge.config import Paper
from mystery_forge.game import AssembledPuzzle, Game
from mystery_forge.i18n import text
from mystery_forge.render.internal_ids import printed_ids
from mystery_forge.render.layout import SAFE_HEIGHT_MM, Tightness, tightness
from mystery_forge.render.sheets import Sheet

HINTS_GROUP: Final[str] = "hints"
SAFE_WIDTH_MM: Final[float] = 186
# The card grids, from small cards to one card per sheet, as (columns, rows). A long hint text needs a bigger card.
CARD_LAYOUTS: Final[tuple[tuple[int, int], ...]] = ((2, 3), (2, 2), (2, 1), (1, 1))
CARD_LABEL_MM: Final[float] = 10
CARD_SIDE_PADDING_MM: Final[float] = 10
CARD_CHAR_MM: Final[float] = 1.9
CARD_LINE_MM: Final[float] = 4.8


@dataclass(frozen=True)
class HintCard:
    code: str
    title: str
    label: str
    text: str
    is_answer: bool


@dataclass(frozen=True)
class HintCardsPage:
    cards: list[HintCard]
    columns: int = 2
    rows: int = 3


@dataclass(frozen=True)
class WarningContent:
    output: str
    title: str


def puzzle_order_key(puzzle: AssembledPuzzle) -> tuple[str, int]:
    return (puzzle.code[0], int(puzzle.code[1:]))


def puzzle_cards(game: Game, puzzle: AssembledPuzzle) -> list[HintCard]:
    language: str = game.config.language
    source = puzzle.source
    cards: list[HintCard] = [
        HintCard(
            puzzle.code,
            source.title,
            text(language, "hint_label", level=str(hint.level)),
            printed_ids(game, hint.text),
            False,
        )
        for hint in source.hints
    ]
    cards.append(HintCard(puzzle.code, source.title, text(language, "answer_label"), source.answer, True))
    return cards


def card_capacity(paper: Paper, columns: int, rows: int) -> int:
    """How many characters of hint text fit the inside half of one card in this grid."""
    half_mm: float = SAFE_HEIGHT_MM[paper] / rows / 2 - CARD_LABEL_MM
    chars_per_line: int = int((SAFE_WIDTH_MM / columns - CARD_SIDE_PADDING_MM) / CARD_CHAR_MM)
    return int(half_mm / CARD_LINE_MM) * chars_per_line


def card_layout(paper: Paper, longest_text: int, level: int) -> tuple[int, int]:
    """The smallest card grid whose cards hold the longest hint, made bigger by the tightness level."""
    fitting: int = next(
        (
            index
            for index, (columns, rows) in enumerate(CARD_LAYOUTS)
            if longest_text <= card_capacity(paper, columns, rows)
        ),
        len(CARD_LAYOUTS) - 1,
    )
    return CARD_LAYOUTS[min(max(fitting, level), len(CARD_LAYOUTS) - 1)]


def hint_sheets(game: Game, levels: Tightness | None = None) -> list[Sheet]:
    cards: list[HintCard] = [
        card for puzzle in sorted(game.puzzles, key=puzzle_order_key) for card in puzzle_cards(game, puzzle)
    ]
    longest: int = max((len(card.text) for card in cards), default=0)
    columns, rows = card_layout(game.config.equipment.paper, longest, tightness(levels or {}, HINTS_GROUP))
    per_sheet: int = columns * rows
    sheets: list[Sheet] = [
        Sheet(role="warning", template="warning.html.j2", content=WarningContent("hints", game.story.title))
    ]
    sheets.extend(
        Sheet(
            role="hint-cards",
            template="hint_cards.html.j2",
            content=HintCardsPage(cards[start : start + per_sheet], columns, rows),
            group=HINTS_GROUP,
        )
        for start in range(0, len(cards), per_sheet)
    )
    return sheets
