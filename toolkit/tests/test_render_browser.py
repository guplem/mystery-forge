"""End-to-end render tests with a real Chromium-based browser (`adr/0007-testing-strategy.md`)."""

import re
import struct
from collections.abc import Iterator
from pathlib import Path

import pytest
from test_render_support import configured, golden_game, showcase_game

from mystery_forge.assemble import assemble_game
from mystery_forge.game import Game
from mystery_forge.mechanics.registry import all_implementations
from mystery_forge.render import materials
from mystery_forge.render.answer_register import register_form
from mystery_forge.render.game_renderer import RenderReport, render_game
from mystery_forge.render.pdf import PlaywrightSheetBrowser, open_sheet_browser
from mystery_forge.spec.documents import ARTIFACT_MARK

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def browser() -> Iterator[PlaywrightSheetBrowser]:
    with open_sheet_browser() as opened:
        yield opened


@pytest.fixture(scope="module")
def golden_report(browser: PlaywrightSheetBrowser, tmp_path_factory: pytest.TempPathFactory) -> RenderReport:
    return render_game(golden_game(), tmp_path_factory.mktemp("golden"), browser)


def pdf_page_count(path: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", path.read_bytes()))


def png_size(path: Path) -> tuple[int, int]:
    width, height = struct.unpack(">II", path.read_bytes()[16:24])
    return width, height


def test_the_golden_game_renders_four_html_and_four_pdf_files(golden_report: RenderReport) -> None:
    names = sorted(path.name for path in golden_report.files)
    assert names == sorted(
        [
            "manual.html",
            "materials.html",
            "hints.html",
            "solutions.html",
            "1 - START HERE (manual).pdf",
            "2 - PRINT THIS (game materials).pdf",
            "3 - Hints.pdf",
            "4 - Solutions.pdf",
        ]
    )
    for output in golden_report.outputs.values():
        assert output.sheet_count > 0
        assert output.pdf_file is not None
        assert output.pdf_file.read_bytes().startswith(b"%PDF")
        assert pdf_page_count(output.pdf_file) == output.sheet_count
        assert len(output.sheet_texts) == output.sheet_count
    assert golden_report.findings == []


def test_every_sheet_has_a_preview_image_at_about_a_third_of_its_size(golden_report: RenderReport) -> None:
    assert len(golden_report.previews) == sum(output.sheet_count for output in golden_report.outputs.values())
    assert all(path.is_file() for path in golden_report.previews)
    width, height = png_size(golden_report.previews[0])
    assert 250 <= width <= 300 and 360 <= height <= 420


def test_the_materials_reveal_no_answer_before_its_puzzle_is_solved(golden_report: RenderReport) -> None:
    game = golden_game()
    materials = golden_report.outputs["materials"]
    stage_order: list[str] = [stage.id for stage in game.flow.stages]
    sheets = list(zip(materials.sheet_texts, materials.sheet_roles, materials.sheet_stages, strict=True))
    register_text: str = " ".join(text for text, role, _ in sheets if role == "register")
    for puzzle in game.puzzles:
        assert register_form(puzzle.source.answer) in register_text
        answer: str = puzzle.source.answer.casefold()
        solved_in: int = stage_order.index(puzzle.source.stage)
        for text, role, stage in sheets:
            before_solved: bool = stage is None or stage_order.index(stage) <= solved_in
            if role not in ("document", "register", "register-results") and before_solved:
                assert answer not in text.casefold(), (puzzle.source.id, role)


def test_the_first_hints_page_spoils_nothing(golden_report: RenderReport) -> None:
    first_page: str = golden_report.outputs["hints"].sheet_texts[0].casefold()
    for puzzle in golden_game().puzzles:
        assert puzzle.source.answer.casefold() not in first_page
        for hint in puzzle.source.hints:
            assert hint.text.casefold() not in first_page
    assert "spoiler" in first_page


def test_every_artifact_on_the_page_is_read_back(golden_report: RenderReport) -> None:
    marked: set[str] = {
        puzzle.source.id
        for puzzle in golden_game().puzzles
        if any(
            ARTIFACT_MARK.format(puzzle=puzzle.source.id) in document.body_html for document in golden_game().documents
        )
    }
    assert set(golden_report.artifacts) == marked
    assert golden_report.artifacts["P1"].text == "NHBV"
    assert "mf-cipher" in golden_report.artifacts["P1"].html


def test_a_document_that_is_too_long_is_reported(browser: PlaywrightSheetBrowser, tmp_path: Path) -> None:
    game = golden_game()
    documents = list(game.documents)
    long_body: str = "".join(
        f"<p>The keeper wrote line {number} of a very long logbook entry.</p>" for number in range(90)
    )
    documents[4] = documents[4].model_copy(update={"body_html": long_body})
    report = render_game(game.model_copy(update={"documents": documents}), tmp_path, browser)
    assert [(finding.rule, finding.file) for finding in report.findings] == [("render.overflow", "documents/D5.md")]


def test_a_slightly_rotated_handwriting_block_that_fits_is_no_overflow(
    browser: PlaywrightSheetBrowser, tmp_path: Path
) -> None:
    game = golden_game()
    documents = list(game.documents)
    lines: str = " ".join(f"The keeper wrote line {number} of his note in a hurry." for number in range(24))
    documents[4] = documents[4].model_copy(update={"body_html": f'<div class="mf-handwriting"><p>{lines}</p></div>'})
    report = render_game(game.model_copy(update={"documents": documents}), tmp_path, browser)
    assert report.findings == []


def test_an_overflow_finding_says_how_much_and_what_overflows(browser: PlaywrightSheetBrowser, tmp_path: Path) -> None:
    game = golden_game()
    documents = list(game.documents)
    long_body: str = "".join(
        f'<div class="mf-handwriting"><p>Line {number} of a long note.</p></div>' for number in range(60)
    )
    documents[4] = documents[4].model_copy(update={"body_html": long_body})
    report = render_game(game.model_copy(update={"documents": documents}), tmp_path, browser)
    assert len(report.findings) == 1
    assert re.search(
        r"content \d+ px too tall; the first part past the edge is a handwriting block", report.findings[0].message
    )


@pytest.mark.parametrize(
    ("game", "theme"),
    [
        (configured(golden_game(), equipment={"printer": "black_and_white", "paper": "Letter"}), "noir"),
        (configured(golden_game(), {"host": "game_master", "language": "es"}, equipment={"ink_saving": True}), "kids"),
        (showcase_game(), "scifi"),
        (showcase_game(), "victorian"),
    ],
    ids=["noir-grayscale-letter", "kids-low-ink-spanish-host", "scifi-showcase", "victorian-showcase"],
)
def test_other_themes_and_modes_fit_their_pages(
    browser: PlaywrightSheetBrowser, tmp_path: Path, game: Game, theme: str
) -> None:
    report = render_game(game, tmp_path, browser, theme)  # type: ignore[arg-type]
    assert report.findings == []
    for output in report.outputs.values():
        assert output.pdf_file is not None and pdf_page_count(output.pdf_file) == output.sheet_count


LIVE_GAME: Path = Path(__file__).parent / "fixtures" / "live-toy-factory"


@pytest.fixture(scope="module")
def live_game() -> Game:
    result = assemble_game(LIVE_GAME, all_implementations())
    assert result.game is not None, result.findings
    return result.game


def overflow_rules(report: RenderReport) -> list[tuple[str, str | None]]:
    return [(finding.rule, finding.file) for finding in report.findings if "overflow" in finding.rule]


@pytest.mark.parametrize(
    ("theme", "paper"),
    [("vintage", "A4"), ("kids", "Letter"), ("noir", "Letter")],
)
def test_the_live_game_has_no_toolkit_page_that_overflows(
    browser: PlaywrightSheetBrowser, tmp_path: Path, live_game: Game, theme: str, paper: str
) -> None:
    # A real 6-puzzle game with 13 places, written by an agent. Every page fits on A4. Two documents are too long for
    # the shorter Letter paper: those findings belong to the game writer.
    game = configured(live_game, equipment={"paper": paper})
    report = render_game(game, tmp_path, browser, theme)  # type: ignore[arg-type]
    rules = overflow_rules(report)
    assert all(rule == "render.overflow" and (file or "").startswith("documents/") for rule, file in rules)
    if paper == "A4":
        assert rules == []


def test_the_browser_loop_repairs_an_estimate_that_is_too_optimistic(
    browser: PlaywrightSheetBrowser, tmp_path: Path, live_game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(materials, "RESULT_CHARS_PER_LINE", 90)
    first_plan = [sheet for sheet in materials.materials_sheets(live_game) if sheet.role == "register-results"]
    report = render_game(live_game, tmp_path, browser)
    assert overflow_rules(report) == []
    assert report.outputs["materials"].sheet_roles.count("register-results") > len(first_plan)
