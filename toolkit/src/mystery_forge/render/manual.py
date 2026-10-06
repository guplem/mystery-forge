"""The content of the manual: what to print, how to set up, how to play, and how to score.

The manual is the first file that a user opens, so its first page is the printing checklist with the page count of
every other file. The plan of the other outputs exists before any HTML, so those counts are exact.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from mystery_forge.game import Game
from mystery_forge.i18n import text
from mystery_forge.render.sheets import OUTPUT_FILES, OutputId, Sheet

COMPANION_FILE: str = "companion.html"


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


@dataclass(frozen=True)
class ManualPage:
    first: bool
    last: bool
    title: str
    tagline: str
    sections: list[ManualSection]


def manual_page_count(game: Game) -> int:
    return 4 if game.config.host == "game_master" else 3


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
    rows: list[list[str]] = [
        [OUTPUT_FILES[output].pdf, str(count), printed[output]] for output, count in page_counts.items()
    ]
    if config.assistance.companion_page:
        rows.append([COMPANION_FILE, "-", text(language, "manual_print_companion_file")])
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
    if game.config.equipment.tape_or_glue:
        items.append(text(language, "manual_need_tape"))
    return ManualSection(heading=text(language, "manual_need_title"), checklist=items)


def setup_section(game: Game) -> ManualSection:
    language: str = game.config.language
    steps: list[str] = [text(language, "manual_setup_split"), text(language, "manual_setup_outside")]
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
        steps.append(text(language, "manual_play_accusation"))
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
    elapsed: int = 0
    for stage in game.flow.stages:
        count: int = sum(1 for puzzle in game.puzzles if puzzle.source.stage == stage.id)
        minutes: int = count * game.brief.minutes_per_puzzle
        elapsed += minutes
        rows.append([text(language, "envelope_label", stage=stage.id), str(count), str(minutes), str(elapsed)])
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


def manual_sheets(game: Game, other_counts: Mapping[OutputId, int]) -> list[Sheet]:
    """Plan the manual. `other_counts` holds the sheet count of each other output that the render writes."""
    counts: dict[OutputId, int] = {"manual": manual_page_count(game), **other_counts}
    last_sections: list[ManualSection] = [
        section for section in (help_section(game), scoring_section(game), personal_section(game)) if section
    ]
    page_sections: list[list[ManualSection]] = [
        [checklist_section(game, counts), needs_section(game)],
        [setup_section(game), play_section(game)],
        last_sections,
    ]
    if game.config.host == "game_master":
        page_sections.append([host_section(game)])
    return [
        Sheet(
            role="manual",
            template="manual.html.j2",
            content=ManualPage(
                first=index == 0,
                last=index == len(page_sections) - 1,
                title=game.story.title,
                tagline=game.story.tagline,
                sections=sections,
            ),
        )
        for index, sections in enumerate(page_sections)
    ]
