"""The sheet plan of the solutions: a cover with no spoilers, one puzzle per page, then the deduction and the truth.

Every step shows the clues that it uses as `document title: "quote"`, so a reader can find the proof in the papers.
"""

from dataclasses import dataclass

from mystery_forge.game import Game
from mystery_forge.render.hints import WarningContent, puzzle_order_key
from mystery_forge.render.sheets import Sheet, SheetRole, paginate
from mystery_forge.spec.models import Clue, Epilogue

# A rough count of printed lines on one page of the deduction and truth sections.
LINES_PER_SHEET: int = 52
CHARACTERS_PER_LINE: int = 80


@dataclass(frozen=True)
class Citation:
    document: str
    quote: str


@dataclass(frozen=True)
class Explained:
    """A statement with the clues that prove it: a solution step, a deduction answer, an exclusion, a reveal step."""

    heading: str
    text: str
    citations: list[Citation]
    points: int = 0


@dataclass(frozen=True)
class SolutionPage:
    code: str
    title: str
    answer: str
    accepted: list[str]
    steps: list[Explained]


@dataclass(frozen=True)
class SectionPage:
    """One page of a section made of explained statements: the deduction, or the truth and its reveal."""

    first: bool
    intro: str
    items: list[Explained]
    subtitle_before: dict[int, str]


@dataclass(frozen=True)
class EpilogueView:
    min_score_percent: int
    title: str
    text: str


@dataclass(frozen=True)
class EpiloguesPage:
    epilogues: list[EpilogueView]


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


def explained_lines(item: Explained) -> int:
    characters: int = len(item.heading) + len(item.text) + sum(len(c.document) + len(c.quote) for c in item.citations)
    return 2 + len(item.citations) + characters // CHARACTERS_PER_LINE


def section_sheets(
    role: SheetRole, template: str, intro: str, items: list[Explained], subtitles: dict[int, str]
) -> list[Sheet]:
    """Paginate a section. `subtitles` maps an item index to a heading printed before that item."""
    indexed: list[tuple[int, Explained]] = list(enumerate(items))
    # A section with no items still gets its page, because the intro (the truth) must print.
    pages: list[list[tuple[int, Explained]]] = paginate(
        indexed,
        lambda pair: explained_lines(pair[1]) + (2 if pair[0] in subtitles else 0),
        LINES_PER_SHEET - len(intro) // CHARACTERS_PER_LINE,
    ) or [[]]
    return [
        Sheet(
            role=role,
            template=template,
            content=SectionPage(
                first=page_index == 0,
                intro=intro if page_index == 0 else "",
                items=[item for _, item in page],
                subtitle_before={
                    position: subtitles[index] for position, (index, _) in enumerate(page) if index in subtitles
                },
            ),
        )
        for page_index, page in enumerate(pages)
    ]


def deduction_sheets(game: Game) -> list[Sheet]:
    deduction = game.story.deduction
    if deduction is None:
        return []
    names: dict[str, str] = {character.id: character.name for character in game.story.characters}
    answers: list[Explained] = [
        Explained(
            heading=question.prompt,
            text=next(option.text for option in question.options if option.id == question.correct),
            citations=citations(game, question.proven_by),
            points=question.points,
        )
        for question in deduction.questions
    ]
    exclusions: list[Explained] = [
        Explained(
            heading=names.get(item.suspect, item.suspect), text=item.explanation, citations=citations(game, item.clues)
        )
        for item in deduction.exclusions
    ]
    subtitles: dict[int, str] = {len(answers): "exclusions"} if exclusions else {}
    return section_sheets("deduction", "deduction.html.j2", "", [*answers, *exclusions], subtitles)


def truth_sheets(game: Game) -> list[Sheet]:
    reveal: list[Explained] = [
        Explained(heading="", text=step.text, citations=citations(game, step.clues)) for step in game.story.reveal
    ]
    return section_sheets("truth", "truth.html.j2", game.story.truth, reveal, {0: "reveal"} if reveal else {})


def solution_page(game: Game, puzzle_index: int) -> Sheet:
    puzzle = game.puzzles[puzzle_index]
    source = puzzle.source
    steps: list[Explained] = [
        Explained(heading="", text=step.text, citations=citations(game, step.uses)) for step in source.solution
    ]
    content = SolutionPage(puzzle.code, source.title, source.answer, list(source.accepted), steps)
    return Sheet(role="solution", template="solution.html.j2", content=content, stage=source.stage)


def epilogues_sheet(epilogues: list[Epilogue]) -> Sheet:
    views: list[EpilogueView] = [
        EpilogueView(epilogue.min_score_percent, epilogue.title, epilogue.text)
        for epilogue in sorted(epilogues, key=lambda item: -item.min_score_percent)
    ]
    return Sheet(role="epilogues", template="epilogues.html.j2", content=EpiloguesPage(views))


def solution_sheets(game: Game) -> list[Sheet]:
    order: list[int] = sorted(range(len(game.puzzles)), key=lambda index: puzzle_order_key(game.puzzles[index]))
    return [
        Sheet(role="warning", template="warning.html.j2", content=WarningContent("solutions", game.story.title)),
        *(solution_page(game, index) for index in order),
        *deduction_sheets(game),
        *truth_sheets(game),
        epilogues_sheet(game.story.epilogues),
    ]
