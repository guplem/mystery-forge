"""The sheet plan of the hints: a cover with no spoilers, then fold cards on a cut grid.

Each card has an outside half (puzzle code, puzzle title, "Hint 1") and an inside half with the text, printed
upside down over a hatch band. Players fold the card so the text is hidden until they turn it over.
The first page carries no hint text, so a file thumbnail or a quick look does not spoil anything.
"""

from dataclasses import dataclass
from typing import Final

from mystery_forge.game import AssembledPuzzle, Game
from mystery_forge.i18n import text
from mystery_forge.render.sheets import Sheet

CARDS_PER_SHEET: Final[int] = 6


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
        HintCard(puzzle.code, source.title, text(language, "hint_label", level=str(hint.level)), hint.text, False)
        for hint in source.hints
    ]
    cards.append(HintCard(puzzle.code, source.title, text(language, "answer_label"), source.answer, True))
    return cards


def hint_sheets(game: Game) -> list[Sheet]:
    cards: list[HintCard] = [
        card for puzzle in sorted(game.puzzles, key=puzzle_order_key) for card in puzzle_cards(game, puzzle)
    ]
    sheets: list[Sheet] = [
        Sheet(role="warning", template="warning.html.j2", content=WarningContent("hints", game.story.title))
    ]
    sheets.extend(
        Sheet(
            role="hint-cards",
            template="hint_cards.html.j2",
            content=HintCardsPage(cards[start : start + CARDS_PER_SHEET]),
        )
        for start in range(0, len(cards), CARDS_PER_SHEET)
    )
    return sheets
