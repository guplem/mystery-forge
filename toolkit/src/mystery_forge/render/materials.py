"""The sheet plan of the game materials: what the players print, split into envelopes, and hold in their hands.

The order of the stack is the order of the setup: first the pages that stay outside the envelopes (cover, envelope
labels, answer register, detective notes), then each stage behind its STOP cover sheet. The accusation form closes
the last stage, so it travels in the last envelope.
"""

import math
from dataclasses import dataclass, replace
from typing import Final

from markupsafe import Markup

from mystery_forge.answers import normalize_answer
from mystery_forge.game import AssembledDocument, Game
from mystery_forge.i18n import text
from mystery_forge.render.answer_register import AnswerRegister, RegisterEntry, ResultParagraph, build_answer_register
from mystery_forge.render.document_body import insert_artifacts, insert_images, split_pages
from mystery_forge.render.kinds import DocumentKind, document_kind
from mystery_forge.render.layout import Tightness, page_budget, split_text, text_height, tightness
from mystery_forge.render.sheets import Sheet, paginate
from mystery_forge.spec.models import AccusationQuestion, Stage

# The flow groups of the materials. The sizes are millimetres on the printed page, as `themes/base.css` sets them.
REGISTER_GROUP: Final[str] = "register"
RESULTS_GROUP: Final[str] = "results"
NOTES_GROUP: Final[str] = "notes"
ACCUSATION_GROUP: Final[str] = "accusation"
LABELS_GROUP: Final[str] = "labels"
# The sheet header (kicker and title) plus the intro paragraph under it.
HEADER_MM: Final[float] = 46
REGISTER_COLUMNS: Final[int] = 3
REGISTER_ROW_MM: Final[float] = 4.8
REGISTER_CHARS_PER_ROW: Final[int] = 16
# The result paragraphs sit in two columns, and a column never splits a paragraph, so a column wastes some space.
RESULT_COLUMNS: Final[int] = 2
RESULT_COLUMN_FILL: Final[float] = 0.92
RESULT_CHARS_PER_LINE: Final[int] = 46
RESULT_LINE_MM: Final[float] = 4.7
RESULT_FRAME_MM: Final[float] = 13
NOTES_SUSPECT_ROW_MM: Final[float] = 12
NOTES_PLACE_ROW_MM: Final[float] = 7.5
NOTES_TABLE_HEAD_MM: Final[float] = 21
NOTES_FREE_LINES_MM: Final[float] = 32
NOTES_MIN_PLACES: Final[int] = 3
ACCUSATION_RESERVED_MM: Final[float] = HEADER_MM + 26
ACCUSATION_CHARS_PER_LINE: Final[int] = 80
LABEL_ROW_MM: Final[float] = 60


@dataclass(frozen=True)
class CoverContent:
    title: str
    tagline: str
    players: int
    names: tuple[str, ...]
    minutes: int
    dedication: str


@dataclass(frozen=True)
class StageCoverContent:
    envelope: str
    open_text: str
    stage_label: str
    opening_text: str


@dataclass(frozen=True)
class DocumentPage:
    document_id: str
    kind: DocumentKind
    title: str
    fields: dict[str, str]
    html: Markup
    page_number: int
    page_count: int
    puzzle_code: str | None
    cut: bool
    fold: bool
    note: str
    copy_number: int
    copies: int


@dataclass(frozen=True)
class RegisterPage:
    entries: list[RegisterEntry]
    first: bool


@dataclass(frozen=True)
class ResultsPage:
    paragraphs: list[ResultParagraph]
    first: bool


@dataclass(frozen=True)
class AccusationContent:
    questions: list[AccusationQuestion]
    total_points: int
    # The number of the first question on this page, and whether this page opens or closes the form.
    start: int = 1
    first: bool = True
    last: bool = True


@dataclass(frozen=True)
class EnvelopeLabel:
    stage: str
    envelope: str
    open_text: str


@dataclass(frozen=True)
class EnvelopeLabelsContent:
    title: str
    labels: list[EnvelopeLabel]


@dataclass(frozen=True)
class DetectiveNotesContent:
    """One notes page. The places are the rows of the "who was where" grid, and the suspects are its columns."""

    suspects: list[str]
    locations: list[str]
    first: bool = True
    last: bool = True


def puzzle_codes(game: Game) -> dict[str, str]:
    return {puzzle.source.id: puzzle.code for puzzle in game.puzzles}


def stage_open_text(game: Game, stage: Stage, label_form: bool) -> str:
    language: str = game.config.language
    if stage.opens_with == "start":
        return text(language, "label_open_start" if label_form else "stage_open_at_start")
    code: str = puzzle_codes(game).get(stage.opens_with, stage.opens_with)
    return text(language, "label_open_after" if label_form else "stage_open_when", code=code)


def cover_sheet(game: Game) -> Sheet:
    config = game.config
    content = CoverContent(
        title=game.story.title,
        tagline=game.story.tagline,
        players=config.players.count,
        names=config.players.names,
        minutes=config.duration_minutes,
        dedication=config.personalization.dedication,
    )
    return Sheet(role="cover", template="cover.html.j2", content=content)


def stage_cover_sheet(game: Game, stage: Stage) -> Sheet:
    content = StageCoverContent(
        envelope=text(game.config.language, "envelope_label", stage=stage.id),
        open_text=stage_open_text(game, stage, label_form=False),
        stage_label=stage.label,
        opening_text=stage.opening_text,
    )
    return Sheet(role="stage-cover", template="stage_cover.html.j2", content=content, stage=stage.id)


def document_sort_key(document: AssembledDocument) -> tuple[int, int]:
    return (document.meta.order, int(document.meta.id[1:]))


def document_sheets(game: Game, document: AssembledDocument) -> list[Sheet]:
    meta = document.meta
    artifacts = {puzzle.source.id: puzzle.artifact for puzzle in game.puzzles}
    body: str = insert_images(insert_artifacts(document.body_html, artifacts), game.images)
    pages: list[str] = split_pages(body)
    code: str | None = puzzle_codes(game).get(meta.puzzle) if meta.puzzle else None
    return [
        Sheet(
            role="document",
            template="document.html.j2",
            content=DocumentPage(
                document_id=meta.id,
                kind=document_kind(meta.kind),
                title=meta.title,
                fields=meta.fields,
                # The assembler and the mechanics build this HTML and escape every text in it.
                html=Markup(page),
                page_number=page_number,
                page_count=len(pages),
                puzzle_code=code,
                cut=meta.print.cut,
                fold=meta.print.fold,
                note=meta.print.note,
                copy_number=copy_number,
                copies=meta.copies,
            ),
            stage=meta.stage,
        )
        for copy_number in range(1, meta.copies + 1)
        for page_number, page in enumerate(pages, start=1)
    ]


def stage_sheets(game: Game, stage: Stage) -> list[Sheet]:
    documents: list[AssembledDocument] = sorted(
        (document for document in game.documents if document.meta.stage == stage.id), key=document_sort_key
    )
    sheets: list[Sheet] = [stage_cover_sheet(game, stage)]
    for document in documents:
        sheets.extend(document_sheets(game, document))
    return sheets


def result_height(paragraph: ResultParagraph) -> float:
    parts: list[str] = [part for part in (paragraph.message, paragraph.reveals, paragraph.action) if part]
    return RESULT_FRAME_MM + sum(text_height(part, RESULT_CHARS_PER_LINE, RESULT_LINE_MM) for part in parts)


def split_result(paragraph: ResultParagraph, column_mm: float) -> list[ResultParagraph]:
    """Split a paragraph taller than one column: its `reveals` text goes on in parts with the same number."""
    if result_height(paragraph) <= column_mm:
        return [paragraph]
    lines: int = max(1, int((column_mm - RESULT_FRAME_MM) / RESULT_LINE_MM) - 4)
    pieces: list[str] = split_text(paragraph.reveals, lines * RESULT_CHARS_PER_LINE) or [""]
    return [
        replace(
            paragraph,
            message=paragraph.message if index == 0 else "",
            reveals=piece,
            action=paragraph.action if index == len(pieces) - 1 else "",
            continued=index > 0,
        )
        for index, piece in enumerate(pieces)
    ]


def register_sheets(game: Game, levels: Tightness) -> list[Sheet]:
    register: AnswerRegister = build_answer_register(game)
    paper = game.config.equipment.paper
    rows: float = page_budget(paper, HEADER_MM, tightness(levels, REGISTER_GROUP)) / REGISTER_ROW_MM
    entry_pages = paginate(
        register.entries,
        lambda entry: math.ceil(len(entry.text) / REGISTER_CHARS_PER_ROW),
        int(rows) * REGISTER_COLUMNS,
    )
    column_mm: float = page_budget(paper, HEADER_MM, tightness(levels, RESULTS_GROUP)) * RESULT_COLUMN_FILL
    parts: list[ResultParagraph] = [
        part for paragraph in register.paragraphs for part in split_result(paragraph, column_mm)
    ]
    result_pages = paginate(parts, result_height, column_mm * RESULT_COLUMNS)
    return [
        *(
            Sheet(
                role="register",
                template="register.html.j2",
                content=RegisterPage(entries, first=index == 0),
                group=REGISTER_GROUP,
            )
            for index, entries in enumerate(entry_pages)
        ),
        *(
            Sheet(
                role="register-results",
                template="results.html.j2",
                content=ResultsPage(items, first=index == 0),
                group=RESULTS_GROUP,
            )
            for index, items in enumerate(result_pages)
        ),
    ]


def envelope_labels_sheets(game: Game, levels: Tightness) -> list[Sheet]:
    labels: list[EnvelopeLabel] = [
        EnvelopeLabel(
            stage=stage.id,
            envelope=text(game.config.language, "envelope_label", stage=stage.id),
            open_text=stage_open_text(game, stage, label_form=True),
        )
        for stage in game.flow.stages
    ]
    budget: float = page_budget(game.config.equipment.paper, HEADER_MM, tightness(levels, LABELS_GROUP))
    per_sheet: int = 2 * max(1, int(budget / LABEL_ROW_MM))
    return [
        Sheet(
            role="envelope-labels",
            template="envelope_labels.html.j2",
            content=EnvelopeLabelsContent(title=game.story.title, labels=labels[start : start + per_sheet]),
            group=LABELS_GROUP,
        )
        for start in range(0, len(labels), per_sheet)
    ]


def notes_places(game: Game) -> list[str]:
    # A place whose name holds an answer ("the boathouse" for BOATHOUSE) stays off the grid: the notes page is in the
    # players' hands from the start. Every suspect stays, because a missing suspect would point at the culprit.
    answers: set[str] = {answer for puzzle in game.puzzles for answer in puzzle.accepted_normalized if answer}
    return [
        location.name
        for location in game.story.locations
        if not any(answer in normalize_answer(location.name, game.config.language) for answer in answers)
    ]


def detective_notes_sheets(game: Game, levels: Tightness) -> list[Sheet]:
    """The suspect table and the free notes, plus the "who was where" grid on as many pages as it needs."""
    characters = game.story.characters
    suspects: list[str] = [character.name for character in characters if character.is_suspect] or [
        character.name for character in characters
    ]
    places: list[str] = notes_places(game)
    budget: float = page_budget(game.config.equipment.paper, HEADER_MM, tightness(levels, NOTES_GROUP))
    free_mm: float = budget - NOTES_TABLE_HEAD_MM - NOTES_FREE_LINES_MM
    first_rows: int = int((free_mm - NOTES_TABLE_HEAD_MM - NOTES_SUSPECT_ROW_MM * len(suspects)) / NOTES_PLACE_ROW_MM)
    first_rows = first_rows if first_rows >= NOTES_MIN_PLACES else 0
    later_rows: int = max(NOTES_MIN_PLACES, int(free_mm / NOTES_PLACE_ROW_MM))
    chunks: list[list[str]] = [places[:first_rows]]
    chunks.extend(places[start : start + later_rows] for start in range(first_rows, len(places), later_rows))
    return [
        Sheet(
            role="detective-notes",
            template="detective_notes.html.j2",
            content=DetectiveNotesContent(
                suspects=suspects, locations=chunk, first=index == 0, last=index == len(chunks) - 1
            ),
            group=NOTES_GROUP,
        )
        for index, chunk in enumerate(chunks)
    ]


def question_height(question: AccusationQuestion) -> float:
    option_rows: int = math.ceil(sum(len(option.text) + 10 for option in question.options) / ACCUSATION_CHARS_PER_LINE)
    return 26 + text_height(question.prompt, ACCUSATION_CHARS_PER_LINE, 5.5) + option_rows * 7


def accusation_sheets(game: Game, questions: list[AccusationQuestion], stage: str, levels: Tightness) -> list[Sheet]:
    budget: float = page_budget(
        game.config.equipment.paper, ACCUSATION_RESERVED_MM, tightness(levels, ACCUSATION_GROUP)
    )
    pages = paginate(questions, question_height, budget)
    total: int = sum(question.points for question in questions)
    starts: list[int] = [1 + sum(len(page) for page in pages[:index]) for index in range(len(pages))]
    return [
        Sheet(
            role="accusation",
            template="accusation.html.j2",
            content=AccusationContent(
                questions=page,
                total_points=total,
                start=starts[index],
                first=index == 0,
                last=index == len(pages) - 1,
            ),
            stage=stage,
            group=ACCUSATION_GROUP,
        )
        for index, page in enumerate(pages)
    ]


def materials_sheets(game: Game, levels: Tightness | None = None) -> list[Sheet]:
    """Plan the materials. `levels` holds the tightness level of each flow group (see `layout.py`)."""
    tight: Tightness = levels or {}
    config = game.config
    sheets: list[Sheet] = [cover_sheet(game)]
    if config.equipment.envelopes:
        sheets.extend(envelope_labels_sheets(game, tight))
    if config.assistance.paper_answer_check:
        sheets.extend(register_sheets(game, tight))
    if config.format in ("case_file", "both"):
        sheets.extend(detective_notes_sheets(game, tight))
    for stage in game.flow.stages:
        sheets.extend(stage_sheets(game, stage))
    if game.story.deduction is not None:
        sheets.extend(accusation_sheets(game, game.story.deduction.questions, game.flow.stages[-1].id, tight))
    return sheets
