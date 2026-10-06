from test_render_support import configured, golden_game, with_story

from mystery_forge.game import Game
from mystery_forge.mechanics.base import Artifact
from mystery_forge.render.manual import COMPANION_FILE, ManualPage, ManualSection, manual_page_count, manual_sheets
from mystery_forge.render.sheets import OutputId
from mystery_forge.spec.models import PrintOptions

COUNTS: dict[OutputId, int] = {"materials": 13, "hints": 3, "solutions": 7}


def pages(game: Game, counts: dict[OutputId, int] | None = None) -> list[ManualPage]:
    sheets = manual_sheets(game, COUNTS if counts is None else counts)
    contents = [sheet.content for sheet in sheets]
    assert all(isinstance(content, ManualPage) for content in contents)
    return contents  # type: ignore[return-value]


def section(game: Game, heading: str) -> ManualSection:
    return next(item for page in pages(game) for item in page.sections if item.heading == heading)


def all_text(game: Game) -> str:
    parts: list[str] = []
    for page in pages(game):
        for item in page.sections:
            parts.extend([item.heading, *item.paragraphs, *item.steps, *item.checklist, item.read_aloud])
            if item.table:
                parts.extend(cell for row in item.table.rows for cell in row)
    return "\n".join(parts)


def test_the_first_page_is_the_printing_checklist_with_exact_page_counts() -> None:
    manual = pages(golden_game())
    assert len(manual) == manual_page_count(golden_game()) == 3
    assert manual[0].first and manual[-1].last and not manual[0].last
    checklist = manual[0].sections[0]
    assert checklist.heading == "Printing checklist"
    assert checklist.table is not None
    assert checklist.table.rows == [
        ["1 - START HERE (manual).pdf", "3", "Yes"],
        ["2 - PRINT THIS (game materials).pdf", "13", "Yes"],
        ["3 - Hints.pdf", "3", "Only if you play without a phone or computer"],
        ["4 - Solutions.pdf", "7", "Only if you play without a phone or computer"],
        [COMPANION_FILE, "-", "No: open it on a phone or computer"],
    ]
    assert "Print at 100% (actual size), single-sided, on A4 paper." in checklist.paragraphs[0]
    assert checklist.paragraphs[1].startswith("Color looks best")
    assert "use the Game companion page instead" in checklist.paragraphs[2]


def test_what_you_need_follows_the_equipment() -> None:
    assert section(golden_game(), "What you need").checklist == [
        "2 envelopes",
        "Pencils and an eraser",
        "Some scrap paper",
        "Scissors",
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
    checklist = pages(game)[0].sections[0]
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


def test_a_game_master_gets_a_timing_page() -> None:
    game = configured(golden_game(), {"host": "game_master"})
    manual = pages(game)
    assert len(manual) == manual_page_count(game) == 4
    host = manual[3].sections[0]
    assert host.heading == "Game master guide"
    assert host.table is not None
    assert host.table.rows == [["Envelope A", "2", "12", "12"], ["Envelope B", "1", "6", "18"]]
    assert host.checklist[0] == "If a group is stuck for 10 minutes, give them the next hint."


def test_the_manual_speaks_the_game_language() -> None:
    game = configured(golden_game(), {"language": "es"})
    assert pages(game)[0].sections[0].heading == "Lista de impresión"
