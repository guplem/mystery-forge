from test_render_support import configured, golden_game, with_story

from mystery_forge.game import Game
from mystery_forge.mechanics.base import Artifact
from mystery_forge.render.manual import (
    MANUAL_GROUP,
    ManualBlock,
    ManualPage,
    ManualSection,
    TableData,
    block_height,
    manual_sections,
    manual_sheets,
    section_blocks,
    table_blocks,
    text_blocks,
)
from mystery_forge.render.sheets import OutputId
from mystery_forge.spec.models import PrintOptions

COUNTS: dict[OutputId, int] = {"materials": 13, "hints": 3, "solutions": 7}


def pages(
    game: Game, counts: dict[OutputId, int] | None = None, levels: dict[str, int] | None = None
) -> list[ManualPage]:
    sheets = manual_sheets(game, COUNTS if counts is None else counts, levels)
    assert {sheet.group for sheet in sheets} == {MANUAL_GROUP}
    contents = [sheet.content for sheet in sheets]
    assert all(isinstance(content, ManualPage) for content in contents)
    return contents  # type: ignore[return-value]


def section(game: Game, heading: str) -> ManualSection:
    return next(item for item in manual_sections(game, {"manual": 3, **COUNTS}) if item.heading == heading)


def all_text(game: Game) -> str:
    parts: list[str] = []
    for item in manual_sections(game, {"manual": 3, **COUNTS}):
        parts.extend([item.heading, *item.paragraphs, *item.steps, *item.checklist, item.read_aloud])
        if item.table:
            parts.extend(cell for row in item.table.rows for cell in row)
    return "\n".join(parts)


def blocks(game: Game, levels: dict[str, int] | None = None) -> list[ManualBlock]:
    return [block for page in pages(game, levels=levels) for block in page.blocks]


def test_the_first_page_is_the_printing_checklist_with_exact_page_counts() -> None:
    manual = pages(golden_game())
    assert manual[0].first and manual[-1].last and not manual[0].last
    assert [block.kind for block in manual[0].blocks[:3]] == ["hero", "heading", "paragraph"]
    assert manual[0].blocks[1].text == "Printing checklist"
    assert manual[-1].blocks[-1].kind == "credit"
    checklist = section(golden_game(), "Printing checklist")
    assert checklist.table is not None
    page_count: str = str(len(manual))
    table = next(block.table for block in manual[0].blocks if block.kind == "table")
    assert table is not None and table.rows[0] == ["1 - START HERE (manual).pdf", page_count, "Yes"]
    assert checklist.table.rows == [
        ["1 - START HERE (manual).pdf", "3", "Yes"],
        ["2 - PRINT THIS (game materials).pdf", "13", "Yes"],
        ["HOST ONLY - spoilers/3 - Hints.pdf", "3", "Only if you play without a phone or computer"],
        ["HOST ONLY - spoilers/4 - Solutions.pdf", "7", "Only if you play without a phone or computer"],
        ["Game companion.html", "-", "No: open it on a phone or computer"],
    ]
    assert "Print at 100% (actual size), single-sided, on A4 paper." in checklist.paragraphs[0]
    assert checklist.paragraphs[1].startswith("Color looks best")
    assert "use the Game companion page instead" in checklist.paragraphs[2]


def test_the_first_page_shows_where_to_set_100_percent_in_each_program() -> None:
    first = pages(golden_game())[0]
    box = next(block for block in first.blocks if block.kind == "box")
    assert box.text == "Print at 100%"
    assert box.items == [
        "Chrome: More settings > Scale > Default",
        "Edge: More settings > Scale > Actual size",
        "Adobe Acrobat Reader: Page Sizing & Handling > Actual size",
    ]
    assert block_height(box) > 0
    spanish = next(
        block for block in pages(configured(golden_game(), {"language": "es"}))[0].blocks if block.kind == "box"
    )
    assert spanish.items[0] == "Chrome: Más ajustes > Escala > Predeterminado"


def test_what_you_need_follows_the_equipment() -> None:
    assert section(golden_game(), "What you need").checklist == [
        "2 envelopes",
        "Pencils and an eraser",
        "Some scrap paper",
        "Scissors",
        "Tape or glue for the envelope labels (or write the letter on each envelope)",
    ]
    bare = configured(
        golden_game(),
        equipment={"envelopes": False, "tape_or_glue": True},
        assistance={"hints": False},
    )
    assert section(bare, "What you need").checklist == [
        "2 folders or paper clips, one for each part",
        "Pencils and an eraser",
        "Some scrap paper",
        "Tape or glue",
    ]
    assert "face down in its own pile" in all_text(bare)


def test_a_cut_document_or_a_cut_artifact_needs_scissors() -> None:
    bare = configured(golden_game(), equipment={"envelopes": False}, assistance={"hints": False})
    documents = list(bare.documents)
    documents[0] = documents[0].model_copy(
        update={"meta": documents[0].meta.model_copy(update={"print": PrintOptions(cut=True)})}
    )
    assert "Scissors" in section(bare.model_copy(update={"documents": documents}), "What you need").checklist
    puzzles = list(bare.puzzles)
    puzzles[0] = puzzles[0].model_copy(update={"artifact": Artifact(html="", solver_text="", print_notes=("Cut",))})
    assert "Scissors" in section(bare.model_copy(update={"puzzles": puzzles}), "What you need").checklist


def with_mechanics(game: Game, *mechanics: str) -> Game:
    puzzles = [
        puzzle.model_copy(update={"source": puzzle.source.model_copy(update={"mechanic": mechanic})})
        for puzzle, mechanic in zip(game.puzzles, mechanics, strict=False)
    ]
    return game.model_copy(update={"puzzles": [*puzzles, *game.puzzles[len(puzzles) :]]})


def test_what_you_need_lists_the_items_that_the_puzzles_need() -> None:
    mirror = "A small mirror (or a bright window: hold the page against it and read it from the back)"
    light = "A bright window or a lamp, to hold pages against the light"
    assert mirror not in section(golden_game(), "What you need").checklist
    game = with_mechanics(golden_game(), "overlay-stack", "mirror-writing", "mirror-writing")
    checklist = section(game, "What you need").checklist
    assert checklist[-2:] == [light, mirror]


def test_play_steps_follow_the_answer_checks_and_include_the_intro() -> None:
    play = section(golden_game(), "How to play")
    assert play.read_aloud == golden_game().story.intro
    assert play.paragraphs == ["Open Envelope A. Read this introduction aloud:"]
    assert any("answer register" in step for step in play.steps)
    assert any("Game companion page" in step for step in play.steps)
    assert play.steps[-1] == "At the end, fill in the accusation form together."
    game = configured(golden_game(), assistance={"paper_answer_check": False, "companion_page": False})
    game = with_story(game, deduction=None)
    text = all_text(game)
    assert "answer register and read" not in text
    assert "companion" not in text.lower()
    assert "Accusation and scoring" not in text
    assert "accusation form together" not in text


def test_the_checklist_without_a_companion_page_prints_everything() -> None:
    game = configured(golden_game(), equipment={"printer": "black_and_white"}, assistance={"companion_page": False})
    checklist = section(game, "Printing checklist")
    assert checklist.table is not None
    assert [row[2] for row in checklist.table.rows] == ["Yes", "Yes", "Yes", "Yes"]
    assert checklist.paragraphs[1] == "This game is made for a black-and-white printer."
    assert len(checklist.paragraphs) == 2


def test_scoring_shows_the_point_range_of_each_ending() -> None:
    scoring = section(golden_game(), "Accusation and scoring")
    assert "75 in all" in scoring.paragraphs[0]
    assert scoring.table is not None
    assert scoring.table.rows == [
        ["57 to 75", "Case closed"],
        ["30 to 56", "Close, but not quite"],
        ["0 to 29", "The light stays dark"],
    ]


def test_the_hints_section_follows_the_assistance() -> None:
    assert section(golden_game(), "Hints and solutions").paragraphs[0].startswith("Stuck?")
    game = configured(golden_game(), assistance={"hints": False, "companion_page": False})
    assert section(game, "Hints and solutions").paragraphs == [
        "The solutions explain every puzzle and the whole story. Read them at the end."
    ]


def test_personal_details_appear_only_when_given() -> None:
    assert "For this game" not in all_text(golden_game())
    game = configured(
        golden_game(),
        players={"count": 2, "names": ("Ana", "Ben")},
        personalization={"host_name": "Clara", "place": "", "inside_jokes": (), "dedication": "For Ben."},
    )
    assert section(game, "For this game").paragraphs == ["Your host: Clara", "Detectives: Ana, Ben", "For Ben."]


def test_a_game_master_gets_a_timing_section() -> None:
    game = configured(golden_game(), {"host": "game_master"})
    host = section(game, "Game master guide")
    assert host.table is not None
    # The rows share the 40 minutes of the config by puzzle count, so the table ends at the game length.
    assert host.table.rows == [["Envelope A", "2", "27", "27"], ["Envelope B", "1", "13", "40"]]
    assert host.checklist[0] == "If a group is stuck for 10 minutes, give them the next hint."
    assert "Game master guide" in [block.text for block in blocks(game) if block.kind == "heading"]


def test_the_manual_speaks_the_game_language() -> None:
    game = configured(golden_game(), {"language": "es"})
    assert pages(game)[0].blocks[1].text == "Lista de impresión"


def test_the_printing_checklist_names_the_files_in_the_game_language() -> None:
    checklist = section(configured(golden_game(), {"language": "es"}), "Lista de impresión")
    assert checklist.table is not None
    assert [row[0] for row in checklist.table.rows] == [
        "1 - EMPIEZA AQUÍ (manual).pdf",
        "2 - IMPRIME ESTO (materiales del juego).pdf",
        "SOLO ANFITRIÓN - spoilers/3 - Pistas.pdf",
        "SOLO ANFITRIÓN - spoilers/4 - Soluciones.pdf",
        "Compañero de juego.html",
    ]


def test_every_section_flows_in_order_and_a_heading_never_ends_a_page() -> None:
    game = configured(golden_game(), {"host": "game_master"})
    manual = pages(game)
    headings: list[str] = [block.text for page in manual for block in page.blocks if block.kind == "heading"]
    assert headings == [item.heading for item in manual_sections(game, {"manual": 3, **COUNTS})]
    assert all(page.blocks[-1].kind != "heading" for page in manual)
    steps = [block.number for block in blocks(golden_game()) if block.kind == "step"]
    assert steps[:4] == [1, 2, 3, 4]


def test_a_long_intro_is_split_and_a_tighter_level_uses_more_pages() -> None:
    game = with_story(golden_game(), intro="The lighthouse stood dark all night. " * 260)
    parts = [block for block in blocks(game) if block.kind == "read_aloud"]
    assert len(parts) > 1
    assert " ".join(part.text for part in parts) == game.story.intro.strip()
    assert len(pages(golden_game(), levels={"manual": 4})) > len(pages(golden_game()))


def test_a_long_step_keeps_its_number_on_the_first_part_only() -> None:
    parts = text_blocks("step", "Open the envelope now. " * 200, 100, 3)
    assert [part.number for part in parts] == [3] + [0] * (len(parts) - 1)
    assert all(block_height(part) <= 100 for part in parts)


def test_a_table_too_long_for_a_page_repeats_its_header() -> None:
    table = TableData(headers=["A", "B"], rows=[[str(number), "x"] for number in range(80)])
    parts = table_blocks(table, 120)
    assert len(parts) > 1
    assert all(part.table is not None and part.table.headers == ["A", "B"] for part in parts)
    assert sum(len(part.table.rows) for part in parts if part.table) == 80


def test_a_long_checklist_is_cut_into_blocks() -> None:
    game = configured(golden_game(), equipment={"tape_or_glue": True})
    needs = section(game, "What you need")
    many = ManualSection(heading="x", checklist=[f"item {number}" for number in range(23)])
    lists = [block for block in section_blocks(many, 200) if block.kind == "checklist"]
    assert [len(block.items) for block in lists] == [10, 10, 3]
    assert needs.checklist[-1].startswith("Tape or glue for the envelope labels")


def test_a_solo_game_fills_in_the_accusation_alone() -> None:
    play = section(configured(golden_game(), players={"count": 1}), "How to play")
    assert play.steps[-1] == "At the end, fill in the accusation form."
