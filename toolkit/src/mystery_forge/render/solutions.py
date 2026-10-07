"""The sheet plan of the solutions: a cover with no spoilers, one puzzle per page, then the deduction and the truth.

Every step shows the clues that it uses as `document title: "quote"`, so a reader can find the proof in the papers.
Each part is a flow group: a puzzle with many steps, or a long truth, goes on over "continued" sheets, and one text
that is too long for a whole sheet is split between sentences.
"""

from dataclasses import dataclass, replace
from typing import Final, Literal

from mystery_forge.config import Paper
from mystery_forge.game import Game
from mystery_forge.render.hints import WarningContent, puzzle_order_key
from mystery_forge.render.layout import Tightness, page_budget, split_text, text_height, tightness
from mystery_forge.render.sheets import Sheet, SheetRole, paginate
from mystery_forge.spec.models import Clue

ItemKind = Literal["statement", "truth", "subtitle", "epilogue"]
SOLUTIONS_GROUP: Final[str] = "solutions"
# The sheet header (kicker and title) of every solutions page, and the answer box of a puzzle's first page.
HEADER_MM: Final[float] = 36
ANSWER_BOX_MM: Final[float] = 50
CREDIT_MM: Final[float] = 20
# The text of each kind of item: characters per line and line height in millimetres.
TEXT_METRICS: Final[dict[ItemKind, tuple[int, float]]] = {
    "statement": (92, 5.1),
    "truth": (84, 6.1),
    "subtitle": (60, 7),
    "epilogue": (92, 5.1),
}
# The fixed part of each kind of item: margins, padding, borders, and the heading line.
ITEM_FRAME_MM: Final[dict[ItemKind, float]] = {"statement": 9, "truth": 12, "subtitle": 7, "epilogue": 30}
CITATION_CHARS_PER_LINE: Final[int] = 110
CITATION_LINE_MM: Final[float] = 4.4


@dataclass(frozen=True)
class Citation:
    document: str
    quote: str


@dataclass(frozen=True)
class Explained:
    """One block of a solutions page: a statement with the clues that prove it, a truth paragraph, a subtitle
    (`heading` holds its text key), or an ending (`points` holds its minimum score percent)."""

    heading: str
    text: str
    citations: list[Citation]
    points: int = 0
    kind: ItemKind = "statement"
    continued: bool = False


@dataclass(frozen=True)
class SolutionPage:
    code: str
    title: str
    answer: str
    accepted: list[str]
    steps: list[Explained]
    # The number of the first step on this page. A puzzle's later pages show "continued" and no answer box.
    start: int = 1
    first: bool = True


@dataclass(frozen=True)
class SectionPage:
    """One page of a section: the deduction, the truth and its reveal, or the endings."""

    title_key: str
    first: bool
    last: bool
    items: list[Explained]


def clue_index(game: Game) -> dict[str, Clue]:
    clues: dict[str, Clue] = {clue.id: clue for clue in game.story.clues}
    for puzzle in game.puzzles:
        clues.update({clue.id: clue for clue in puzzle.source.clues})
    return clues


def citations(game: Game, clue_ids: list[str]) -> list[Citation]:
    """Return the citation of each known clue. An unknown id is skipped: the evidence check reports it."""
    clues: dict[str, Clue] = clue_index(game)
    titles: dict[str, str] = {document.meta.id: document.meta.title for document in game.documents}
    return [
        Citation(document=titles.get(clues[clue_id].document, clues[clue_id].document), quote=clues[clue_id].quote)
        for clue_id in clue_ids
        if clue_id in clues
    ]


def item_height(item: Explained) -> float:
    chars_per_line, line_mm = TEXT_METRICS[item.kind]
    heading: float = line_mm if item.heading and item.kind != "subtitle" else 0
    quotes: float = sum(
        text_height(f"{citation.document}: {citation.quote}", CITATION_CHARS_PER_LINE, CITATION_LINE_MM)
        for citation in item.citations
    )
    return ITEM_FRAME_MM[item.kind] + heading + text_height(item.text, chars_per_line, line_mm) + quotes


def fit_item(item: Explained, budget: float) -> list[Explained]:
    """Split an item taller than a whole page: the heading opens the first part, the citations close the last."""
    if item_height(item) <= budget:
        return [item]
    chars_per_line, line_mm = TEXT_METRICS[item.kind]
    room: float = budget - item_height(replace(item, text=""))
    pieces: list[str] = split_text(item.text, max(chars_per_line, int(room / line_mm) * chars_per_line))
    return [
        replace(
            item,
            heading=item.heading if index == 0 else "",
            text=piece,
            citations=item.citations if index == len(pieces) - 1 else [],
            continued=index > 0,
        )
        for index, piece in enumerate(pieces)
    ]


def section_sheets(
    role: SheetRole, title_key: str, items: list[Explained], paper: Paper, levels: Tightness, reserved_mm: float
) -> list[Sheet]:
    budget: float = page_budget(paper, HEADER_MM + reserved_mm, tightness(levels, role))
    fitted: list[Explained] = [part for item in items for part in fit_item(item, budget)]
    pages: list[list[Explained]] = paginate(fitted, item_height, budget, lambda item: item.kind == "subtitle") or [[]]
    return [
        Sheet(
            role=role,
            template="section.html.j2",
            content=SectionPage(title_key=title_key, first=index == 0, last=index == len(pages) - 1, items=page),
            group=role,
        )
        for index, page in enumerate(pages)
    ]


def deduction_sheets(game: Game, levels: Tightness) -> list[Sheet]:
    deduction = game.story.deduction
    if deduction is None:
        return []
    names: dict[str, str] = {character.id: character.name for character in game.story.characters}
    items: list[Explained] = [
        Explained(
            heading=question.prompt,
            text=next(option.text for option in question.options if option.id == question.correct),
            citations=citations(game, question.proven_by),
            points=question.points,
        )
        for question in deduction.questions
    ]
    if deduction.exclusions:
        items.append(Explained(heading="exclusions_title", text="", citations=[], kind="subtitle"))
    items.extend(
        Explained(
            heading=names.get(item.suspect, item.suspect), text=item.explanation, citations=citations(game, item.clues)
        )
        for item in deduction.exclusions
    )
    return section_sheets("deduction", "deduction_title", items, game.config.equipment.paper, levels, 0)


def truth_sheets(game: Game, levels: Tightness) -> list[Sheet]:
    items: list[Explained] = [Explained(heading="", text=game.story.truth, citations=[], kind="truth")]
    if game.story.reveal:
        items.append(Explained(heading="reveal_title", text="", citations=[], kind="subtitle"))
    items.extend(
        Explained(heading="", text=step.text, citations=citations(game, step.clues)) for step in game.story.reveal
    )
    return section_sheets("truth", "truth_title", items, game.config.equipment.paper, levels, 0)


def epilogues_sheets(game: Game, levels: Tightness) -> list[Sheet]:
    items: list[Explained] = [
        Explained(
            heading=epilogue.title, text=epilogue.text, citations=[], points=epilogue.min_score_percent, kind="epilogue"
        )
        for epilogue in sorted(game.story.epilogues, key=lambda item: -item.min_score_percent)
    ]
    return section_sheets("epilogues", "epilogues_title", items, game.config.equipment.paper, levels, CREDIT_MM)


def solution_pages(game: Game, puzzle_index: int, levels: Tightness) -> list[Sheet]:
    """One puzzle: its answer box and its steps, on as many pages as the steps need."""
    puzzle = game.puzzles[puzzle_index]
    source = puzzle.source
    budget: float = page_budget(game.config.equipment.paper, HEADER_MM, tightness(levels, SOLUTIONS_GROUP))
    steps: list[Explained] = [
        part
        for step in source.solution
        for part in fit_item(
            Explained(heading="", text=step.text, citations=citations(game, step.uses)), budget - ANSWER_BOX_MM
        )
    ]
    # The answer box opens the first page: a placeholder of its height keeps the first page short enough.
    answer_box = Explained(heading="", text="", citations=[], kind="subtitle")
    pages: list[list[Explained]] = paginate(
        [answer_box, *steps], lambda item: ANSWER_BOX_MM if item is answer_box else item_height(item), budget
    )
    pages[0] = pages[0][1:]
    starts: list[int] = [
        1 + sum(1 for page in pages[:index] for step in page if not step.continued) for index in range(len(pages))
    ]
    return [
        Sheet(
            role="solution",
            template="solution.html.j2",
            content=SolutionPage(
                puzzle.code,
                source.title,
                source.answer,
                list(source.accepted),
                page,
                start=starts[index],
                first=index == 0,
            ),
            stage=source.stage,
            group=SOLUTIONS_GROUP,
        )
        for index, page in enumerate(pages)
    ]


def solution_sheets(game: Game, levels: Tightness | None = None) -> list[Sheet]:
    tight: Tightness = levels or {}
    order: list[int] = sorted(range(len(game.puzzles)), key=lambda index: puzzle_order_key(game.puzzles[index]))
    return [
        Sheet(role="warning", template="warning.html.j2", content=WarningContent("solutions", game.story.title)),
        *(sheet for index in order for sheet in solution_pages(game, index, tight)),
        *deduction_sheets(game, tight),
        *truth_sheets(game, tight),
        *epilogues_sheets(game, tight),
    ]
