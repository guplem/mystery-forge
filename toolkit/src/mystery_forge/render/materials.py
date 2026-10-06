"""The sheet plan of the game materials: what the players print, split into envelopes, and hold in their hands.

The order of the stack is the order of the setup: first the pages that stay outside the envelopes (cover, envelope
labels, answer register, detective notes), then each stage behind its STOP cover sheet. The accusation form closes
the last stage, so it travels in the last envelope.
"""

from dataclasses import dataclass

from markupsafe import Markup

from mystery_forge.answers import normalize_answer
from mystery_forge.game import AssembledDocument, Game
from mystery_forge.i18n import text
from mystery_forge.render.answer_register import AnswerRegister, RegisterEntry, ResultParagraph, build_answer_register
from mystery_forge.render.document_body import insert_artifacts, insert_images, split_pages
from mystery_forge.render.kinds import DocumentKind, document_kind
from mystery_forge.render.sheets import Sheet, paginate
from mystery_forge.spec.models import AccusationQuestion, Stage

REGISTER_ENTRIES_PER_SHEET: int = 108
# A rough count of printed lines: the result paragraphs sit in two columns of about 40 characters.
RESULT_LINES_PER_SHEET: int = 96
RESULT_CHARACTERS_PER_LINE: int = 40


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
    suspects: list[str]
    locations: list[str]


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


def result_lines(paragraph: ResultParagraph) -> int:
    characters: int = len(paragraph.message) + len(paragraph.action) + len(paragraph.reveals)
    return 3 + characters // RESULT_CHARACTERS_PER_LINE


def register_sheets(game: Game) -> list[Sheet]:
    register: AnswerRegister = build_answer_register(game)
    entry_pages = paginate(register.entries, lambda _: 1, REGISTER_ENTRIES_PER_SHEET)
    result_pages = paginate(register.paragraphs, result_lines, RESULT_LINES_PER_SHEET)
    return [
        *(
            Sheet(role="register", template="register.html.j2", content=RegisterPage(entries, first=index == 0))
            for index, entries in enumerate(entry_pages)
        ),
        *(
            Sheet(role="register-results", template="results.html.j2", content=ResultsPage(items, first=index == 0))
            for index, items in enumerate(result_pages)
        ),
    ]


def envelope_labels_sheet(game: Game) -> Sheet:
    labels: list[EnvelopeLabel] = [
        EnvelopeLabel(
            stage=stage.id,
            envelope=text(game.config.language, "envelope_label", stage=stage.id),
            open_text=stage_open_text(game, stage, label_form=True),
        )
        for stage in game.flow.stages
    ]
    return Sheet(
        role="envelope-labels",
        template="envelope_labels.html.j2",
        content=EnvelopeLabelsContent(title=game.story.title, labels=labels),
    )


def detective_notes_sheet(game: Game) -> Sheet:
    characters = game.story.characters
    suspects: list[str] = [character.name for character in characters if character.is_suspect] or [
        character.name for character in characters
    ]
    # A location whose name holds an answer ("the boathouse" for BOATHOUSE) stays off the grid: the notes page is
    # in the players' hands from the start. Every suspect stays, because a missing suspect would point at the culprit.
    answers: set[str] = {answer for puzzle in game.puzzles for answer in puzzle.accepted_normalized if answer}
    locations: list[str] = [
        location.name
        for location in game.story.locations
        if not any(answer in normalize_answer(location.name, game.config.language) for answer in answers)
    ]
    content = DetectiveNotesContent(suspects=suspects, locations=locations)
    return Sheet(role="detective-notes", template="detective_notes.html.j2", content=content)


def accusation_sheet(game: Game, questions: list[AccusationQuestion], stage: str) -> Sheet:
    content = AccusationContent(questions=questions, total_points=sum(question.points for question in questions))
    return Sheet(role="accusation", template="accusation.html.j2", content=content, stage=stage)


def materials_sheets(game: Game) -> list[Sheet]:
    config = game.config
    sheets: list[Sheet] = [cover_sheet(game)]
    if config.equipment.envelopes:
        sheets.append(envelope_labels_sheet(game))
    if config.assistance.paper_answer_check:
        sheets.extend(register_sheets(game))
    if config.format in ("case_file", "both"):
        sheets.append(detective_notes_sheet(game))
    for stage in game.flow.stages:
        sheets.extend(stage_sheets(game, stage))
    if game.story.deduction is not None:
        sheets.append(accusation_sheet(game, game.story.deduction.questions, game.flow.stages[-1].id))
    return sheets
