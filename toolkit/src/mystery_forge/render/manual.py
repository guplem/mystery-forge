"""The content of the manual: what to print, how to set up, how to play, and how to score.

The manual is the first file that a user opens, so its first page is the printing checklist with the page count of
every other file. The plan of the other outputs exists before any HTML, so those counts are exact. The sections flow
as blocks over as many pages as they need, and a heading never ends a page.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Final, Literal

from mystery_forge.game import Game
from mystery_forge.i18n import join_list, text
from mystery_forge.render.layout import Tightness, page_budget, split_text, text_height, tightness
from mystery_forge.render.sheets import OutputFileNames, OutputId, Sheet, output_file_names, paginate

PRINT_SETTING_KEYS: Final[tuple[str, ...]] = (
    "manual_print_box_chrome",
    "manual_print_box_edge",
    "manual_print_box_acrobat",
)

MANUAL_GROUP: Final[str] = "manual"
# Millimetres on the printed page, as `themes/base.css` sets them. The running header tops every page; the hero block
# (the big title of page 1) and the credit block (the last lines) are blocks of the flow, so only their page pays.
RUNNING_HEADER_MM: Final[float] = 14
FIXED_BLOCK_MM: Final[dict[str, float]] = {"hero": 34, "credit": 18, "heading": 14}
MANUAL_CHARS_PER_LINE: Final[int] = 98
STEP_INDENT_CHARS: Final[int] = 6
CHECKLIST_CHARS_PER_LINE: Final[int] = 40
CHECKLIST_ITEMS_PER_BLOCK: Final[int] = 10
BODY_LINE_MM: Final[float] = 5.2
BLOCK_GAP_MM: Final[float] = 2.6
READ_ALOUD_CHARS_PER_LINE: Final[int] = 92
READ_ALOUD_LINE_MM: Final[float] = 6.2
READ_ALOUD_FRAME_MM: Final[float] = 13
BOX_FRAME_MM: Final[float] = 13
BOX_CHARS_PER_LINE: Final[int] = 90
TABLE_HEAD_MM: Final[float] = 13
TABLE_LINE_MM: Final[float] = 4.9
TABLE_ROW_PADDING_MM: Final[float] = 3.6


@dataclass(frozen=True)
class TableData:
    headers: list[str]
    rows: list[list[str]]


@dataclass(frozen=True)
class ManualSection:
    heading: str
    paragraphs: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    table: TableData | None = None
    read_aloud: str = ""
    # A framed box after the paragraphs: its title and its lines.
    box_title: str = ""
    box_lines: list[str] = field(default_factory=list)


def checklist_section(game: Game, page_counts: Mapping[OutputId, int]) -> ManualSection:
    language: str = game.config.language
    config = game.config
    optional: str = text(language, "manual_print_optional" if config.assistance.companion_page else "manual_print_yes")
    printed: dict[OutputId, str] = {
        "manual": text(language, "manual_print_yes"),
        "materials": text(language, "manual_print_yes"),
        "hints": optional,
        "solutions": optional,
    }
    names: OutputFileNames = output_file_names(language)
    rows: list[list[str]] = [
        [names.exported_path(output), str(count), printed[output]] for output, count in page_counts.items()
    ]
    if config.assistance.companion_page:
        rows.append([names.companion, "-", text(language, "manual_print_companion_file")])
    paragraphs: list[str] = [
        text(language, "manual_print_actual_size", paper=config.equipment.paper),
        text(language, "manual_print_bw" if config.equipment.printer == "black_and_white" else "manual_print_color"),
    ]
    if config.assistance.companion_page:
        paragraphs.append(text(language, "manual_print_skip_spoilers"))
    headers: list[str] = [text(language, key) for key in ("manual_file", "manual_pages", "manual_print_column")]
    return ManualSection(
        heading=text(language, "manual_checklist_title"),
        paragraphs=paragraphs,
        table=TableData(headers=headers, rows=rows),
        box_title=text(language, "manual_print_box_title"),
        box_lines=[text(language, key) for key in PRINT_SETTING_KEYS],
    )


def needs_cutting(game: Game) -> bool:
    cut_documents: bool = any(document.meta.print.cut for document in game.documents)
    cut_artifacts: bool = any(puzzle.artifact is not None and puzzle.artifact.print_notes for puzzle in game.puzzles)
    return game.config.equipment.envelopes or game.config.assistance.hints or cut_documents or cut_artifacts


def needs_section(game: Game) -> ManualSection:
    language: str = game.config.language
    stages: str = str(len(game.flow.stages))
    items: list[str] = [
        text(
            language,
            "manual_need_envelopes" if game.config.equipment.envelopes else "manual_need_folders",
            count=stages,
        ),
        text(language, "manual_need_pencils"),
        text(language, "manual_need_paper"),
    ]
    if needs_cutting(game):
        items.append(text(language, "manual_need_scissors"))
    if game.config.equipment.envelopes:
        items.append(text(language, "manual_need_label_tape"))
    elif game.config.equipment.tape_or_glue:
        items.append(text(language, "manual_need_tape"))
    return ManualSection(heading=text(language, "manual_need_title"), checklist=items)


def outside_pages(game: Game) -> list[str]:
    """The pages before the first STOP page, in the order of `materials_sheets`."""
    config = game.config
    keys: list[str] = ["manual_outside_cover"]
    if config.equipment.envelopes:
        keys.append("manual_outside_labels")
    if config.assistance.paper_answer_check:
        keys.append("manual_outside_register")
    if config.format in ("case_file", "both"):
        keys.append("manual_outside_notes")
    return [text(config.language, key) for key in keys]


def setup_section(game: Game) -> ManualSection:
    language: str = game.config.language
    outside_key: str = "manual_setup_outside" if game.config.equipment.envelopes else "manual_setup_outside_piles"
    steps: list[str] = [
        text(language, "manual_setup_split"),
        text(language, outside_key, pages=join_list(language, outside_pages(game))),
    ]
    steps.append(text(language, "manual_setup_envelopes" if game.config.equipment.envelopes else "manual_setup_piles"))
    steps.append(text(language, "manual_setup_spoilers"))
    return ManualSection(heading=text(language, "manual_setup_title"), steps=steps)


def play_section(game: Game) -> ManualSection:
    language: str = game.config.language
    assistance = game.config.assistance
    steps: list[str] = [text(language, "manual_play_solve")]
    if assistance.paper_answer_check:
        steps.append(text(language, "manual_play_check_register"))
    if assistance.companion_page:
        steps.append(text(language, "manual_play_check_companion"))
    steps.append(text(language, "manual_play_next"))
    if game.story.deduction is not None:
        steps.append(text(language, "manual_play_accusation", solo=game.config.players.count == 1))
    return ManualSection(
        heading=text(language, "manual_play_title"),
        paragraphs=[text(language, "manual_play_open_first")],
        read_aloud=game.story.intro,
        steps=steps,
    )


def help_section(game: Game) -> ManualSection:
    language: str = game.config.language
    paragraphs: list[str] = []
    if game.config.assistance.hints:
        paragraphs.append(text(language, "manual_hints_text"))
    if game.config.assistance.companion_page:
        paragraphs.append(text(language, "manual_hints_companion"))
    paragraphs.append(text(language, "manual_solutions_text"))
    return ManualSection(heading=text(language, "manual_hints_title"), paragraphs=paragraphs)


def rank_rows(game: Game, total_points: int) -> list[list[str]]:
    epilogues = sorted(game.story.epilogues, key=lambda epilogue: -epilogue.min_score_percent)
    rows: list[list[str]] = []
    high: int = total_points
    for epilogue in epilogues:
        low: int = math.ceil(total_points * epilogue.min_score_percent / 100)
        rows.append([text(game.config.language, "manual_rank_range", low=str(low), high=str(high)), epilogue.title])
        high = max(low - 1, 0)
    return rows


def scoring_section(game: Game) -> ManualSection | None:
    if game.story.deduction is None:
        return None
    language: str = game.config.language
    total: int = sum(question.points for question in game.story.deduction.questions)
    headers: list[str] = [text(language, "manual_rank_points"), text(language, "manual_rank_ending")]
    return ManualSection(
        heading=text(language, "manual_scoring_title"),
        paragraphs=[text(language, "manual_scoring_text", total=str(total))],
        table=TableData(headers=headers, rows=rank_rows(game, total)),
    )


def personal_section(game: Game) -> ManualSection | None:
    language: str = game.config.language
    personal = game.config.personalization
    paragraphs: list[str] = []
    if personal.host_name:
        paragraphs.append(text(language, "manual_host_name", name=personal.host_name))
    if game.config.players.names:
        paragraphs.append(text(language, "manual_player_names", names=", ".join(game.config.players.names)))
    if personal.dedication:
        paragraphs.append(personal.dedication)
    return ManualSection(heading=text(language, "manual_personal_title"), paragraphs=paragraphs) if paragraphs else None


def host_section(game: Game) -> ManualSection:
    language: str = game.config.language
    rows: list[list[str]] = []
    # Groups solve in parallel, so puzzles times minutes overshoots: share the config duration by puzzle count.
    total: int = max(1, len(game.puzzles))
    counted: int = 0
    elapsed: int = 0
    for stage in game.flow.stages:
        count: int = sum(1 for puzzle in game.puzzles if puzzle.source.stage == stage.id)
        counted += count
        until: int = round(game.config.duration_minutes * counted / total)
        rows.append([text(language, "envelope_label", stage=stage.id), str(count), str(until - elapsed), str(until)])
        elapsed = until
    headers: list[str] = [
        text(language, key)
        for key in ("manual_host_stage", "manual_host_puzzles", "manual_host_minutes", "manual_host_by")
    ]
    return ManualSection(
        heading=text(language, "manual_host_title"),
        paragraphs=[text(language, "manual_host_intro")],
        table=TableData(headers=headers, rows=rows),
        checklist=[text(language, "manual_host_stuck"), text(language, "manual_host_answers")],
    )


BlockKind = Literal["hero", "heading", "paragraph", "read_aloud", "box", "table", "step", "checklist", "credit"]


@dataclass(frozen=True)
class ManualBlock:
    """One block of the manual flow. A step has its `number`; the second part of a long step has number 0."""

    kind: BlockKind
    text: str = ""
    number: int = 0
    items: list[str] = field(default_factory=list)
    table: TableData | None = None


@dataclass(frozen=True)
class ManualPage:
    first: bool
    last: bool
    title: str
    tagline: str
    blocks: list[ManualBlock]


def table_row_height(row: list[str]) -> float:
    chars_per_cell: int = max(8, MANUAL_CHARS_PER_LINE // max(1, len(row)))
    return max(text_height(cell, chars_per_cell, TABLE_LINE_MM) for cell in row) + TABLE_ROW_PADDING_MM


def block_height(block: ManualBlock) -> float:
    if block.kind in FIXED_BLOCK_MM:
        return FIXED_BLOCK_MM[block.kind]
    if block.kind == "read_aloud":
        return text_height(block.text, READ_ALOUD_CHARS_PER_LINE, READ_ALOUD_LINE_MM) + READ_ALOUD_FRAME_MM
    if block.kind == "box":
        lines: list[str] = [block.text, *block.items]
        return BOX_FRAME_MM + sum(text_height(line, BOX_CHARS_PER_LINE, BODY_LINE_MM) for line in lines)
    if block.kind == "table":
        assert block.table is not None
        return TABLE_HEAD_MM + sum(table_row_height(row) for row in block.table.rows)
    if block.kind == "checklist":
        heights: list[float] = [text_height(item, CHECKLIST_CHARS_PER_LINE, BODY_LINE_MM) + 2 for item in block.items]
        return sum(heights) / 2 + max(heights, default=0) + 2
    chars_per_line: int = MANUAL_CHARS_PER_LINE - (STEP_INDENT_CHARS if block.kind == "step" else 0)
    return text_height(block.text, chars_per_line, BODY_LINE_MM) + BLOCK_GAP_MM


def text_blocks(kind: BlockKind, text_value: str, budget: float, number: int = 0) -> list[ManualBlock]:
    """One text block, or several when the text is too long for one page. A step keeps its number on the first."""
    block = ManualBlock(kind=kind, text=text_value, number=number)
    if block_height(block) <= budget:
        return [block]
    chars_per_line, line_mm = (
        (READ_ALOUD_CHARS_PER_LINE, READ_ALOUD_LINE_MM)
        if kind == "read_aloud"
        else (MANUAL_CHARS_PER_LINE, BODY_LINE_MM)
    )
    pieces: list[str] = split_text(text_value, int((budget - READ_ALOUD_FRAME_MM) / line_mm) * chars_per_line)
    return [replace(block, text=piece, number=number if index == 0 else 0) for index, piece in enumerate(pieces)]


def table_blocks(table: TableData, budget: float) -> list[ManualBlock]:
    """A table, cut into several tables with the same header when its rows do not fit one page."""
    chunks: list[list[list[str]]] = paginate(table.rows, table_row_height, budget - TABLE_HEAD_MM)
    return [ManualBlock(kind="table", table=TableData(headers=table.headers, rows=chunk)) for chunk in chunks]


def section_blocks(section: ManualSection, budget: float) -> list[ManualBlock]:
    blocks: list[ManualBlock] = [ManualBlock(kind="heading", text=section.heading)]
    for paragraph in section.paragraphs:
        blocks.extend(text_blocks("paragraph", paragraph, budget))
    if section.read_aloud:
        blocks.extend(text_blocks("read_aloud", section.read_aloud, budget))
    if section.box_lines:
        blocks.append(ManualBlock(kind="box", text=section.box_title, items=section.box_lines))
    if section.table:
        blocks.extend(table_blocks(section.table, budget))
    for number, step in enumerate(section.steps, start=1):
        blocks.extend(text_blocks("step", step, budget, number))
    for start in range(0, len(section.checklist), CHECKLIST_ITEMS_PER_BLOCK):
        blocks.append(ManualBlock(kind="checklist", items=section.checklist[start : start + CHECKLIST_ITEMS_PER_BLOCK]))
    return blocks


def manual_sections(game: Game, counts: Mapping[OutputId, int]) -> list[ManualSection]:
    sections: list[ManualSection | None] = [
        checklist_section(game, counts),
        needs_section(game),
        setup_section(game),
        play_section(game),
        help_section(game),
        scoring_section(game),
        personal_section(game),
        host_section(game) if game.config.host == "game_master" else None,
    ]
    return [section for section in sections if section is not None]


def manual_pages(game: Game, counts: Mapping[OutputId, int], levels: Tightness) -> list[list[ManualBlock]]:
    budget: float = page_budget(game.config.equipment.paper, RUNNING_HEADER_MM, tightness(levels, MANUAL_GROUP))
    blocks: list[ManualBlock] = [
        ManualBlock(kind="hero"),
        *(block for section in manual_sections(game, counts) for block in section_blocks(section, budget)),
        ManualBlock(kind="credit"),
    ]
    return paginate(blocks, block_height, budget, lambda block: block.kind == "heading")


def manual_sheets(game: Game, other_counts: Mapping[OutputId, int], levels: Tightness | None = None) -> list[Sheet]:
    """Plan the manual. `other_counts` holds the sheet count of each other output that the render writes."""
    tight: Tightness = levels or {}
    # The checklist names the manual's own page count, which the layout decides: plan once to learn it, then again.
    estimate: int = len(manual_pages(game, {"manual": 1, **other_counts}, tight))
    pages: list[list[ManualBlock]] = manual_pages(game, {"manual": estimate, **other_counts}, tight)
    return [
        Sheet(
            role="manual",
            template="manual.html.j2",
            content=ManualPage(
                first=index == 0,
                last=index == len(pages) - 1,
                title=game.story.title,
                tagline=game.story.tagline,
                blocks=blocks,
            ),
            group=MANUAL_GROUP,
        )
        for index, blocks in enumerate(pages)
    ]
