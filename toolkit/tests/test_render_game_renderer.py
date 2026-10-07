import re
from collections.abc import Callable
from pathlib import Path

from test_render_support import configured, golden_game

from mystery_forge.render.game_renderer import (
    MAX_PASSES,
    output_plans,
    render_game,
    sheet_source_files,
    tightened,
)
from mystery_forge.render.pdf import ArtifactReading, BoxMeasurement, PageProbe, SheetMeasurement

# Given the role of every sheet of one output, return the indexes of the sheets that overflow.
OverflowRule = Callable[[list[str]], set[int]]


def nothing_overflows(roles: list[str]) -> set[int]:
    return set()


class FakeSheetBrowser:
    """Measure the sheets that `rule` names as overflowing and every other sheet as fitting. Write nothing."""

    def __init__(self, rule: OverflowRule = nothing_overflows) -> None:
        self.rule: OverflowRule = rule
        self.calls: list[str] = []

    def print_output(self, html: str, pdf_path: Path, preview_paths: list[Path]) -> PageProbe:
        self.calls.append(pdf_path.name)
        roles: list[str] = re.findall(r'<section class="sheet [^"]*" data-role="([^"]+)"', html)
        assert len(roles) == len(preview_paths)
        overflowing: set[int] = self.rule(roles)
        sheets = [
            SheetMeasurement(
                scroll_height=1200 if index in overflowing else 1100,
                client_height=1100,
                scroll_width=800,
                client_width=800,
                boxes=[BoxMeasurement(name="safe", scroll_height=1, client_height=1, scroll_width=1, client_width=1)],
                escaped=0,
                text=f"sheet {index}",
            )
            for index in range(len(roles))
        ]
        artifacts = [ArtifactReading(puzzle="P1", text="NHBV", html="<p>NHBV</p>")] if "data-artifact" in html else []
        return PageProbe(sheets=sheets, artifacts=artifacts)


def test_without_a_browser_the_render_writes_only_html(tmp_path: Path) -> None:
    report = render_game(golden_game(), tmp_path / "out", None)
    assert [path.name for path in report.files] == ["manual.html", "materials.html", "hints.html", "solutions.html"]
    assert all(path.is_file() for path in report.files)
    assert report.theme == "vintage"
    assert report.outputs["materials"].sheet_count == 13
    assert report.outputs["materials"].sheet_roles[2] == "register"
    assert report.outputs["materials"].sheet_stages[-1] == "B"
    assert report.outputs["materials"].pdf_file is None
    assert report.outputs["materials"].sheet_texts == []
    assert report.artifacts == {} and report.previews == [] and report.findings == []


def test_with_a_browser_the_report_carries_pdfs_texts_artifacts_and_overflow(tmp_path: Path) -> None:
    def document_and_warning(roles: list[str]) -> set[int]:
        return {roles.index("document")} if "document" in roles else {0} if roles[0] == "warning" else set()

    browser = FakeSheetBrowser(document_and_warning)
    report = render_game(golden_game(), tmp_path, browser, "noir")
    assert report.theme == "noir"
    assert browser.calls == [
        "1 - START HERE (manual).pdf",
        "2 - PRINT THIS (game materials).pdf",
        "3 - Hints.pdf",
        "4 - Solutions.pdf",
    ]
    assert len(report.files) == 8
    assert len(report.previews) == sum(output.sheet_count for output in report.outputs.values())
    assert report.previews[0] == tmp_path / "previews" / "manual-1.png"
    assert (tmp_path / "previews").is_dir()
    assert report.outputs["hints"].sheet_texts[0] == "sheet 0"
    assert set(report.artifacts) == {"P1"}
    assert [(finding.rule, finding.file) for finding in report.findings] == [
        ("render.overflow", "documents/D1.md"),
        ("render.toolkit_overflow", None),
        ("render.toolkit_overflow", None),
    ]


def test_an_overflowing_flow_group_gets_more_sheets_until_it_fits(tmp_path: Path) -> None:
    def results_until_two(roles: list[str]) -> set[int]:
        results = [index for index, role in enumerate(roles) if role == "register-results"]
        return set(results) if len(results) < 2 else set()

    browser = FakeSheetBrowser(results_until_two)
    report = render_game(golden_game(), tmp_path, browser)
    assert report.findings == []
    assert report.outputs["materials"].sheet_roles.count("register-results") == 2
    assert browser.calls.count("2 - PRINT THIS (game materials).pdf") > 1
    assert browser.calls.count("3 - Hints.pdf") == 1


def test_the_loop_stops_after_the_last_pass_and_reports_a_toolkit_bug(tmp_path: Path) -> None:
    def results_always(roles: list[str]) -> set[int]:
        return {index for index, role in enumerate(roles) if role == "register-results"}

    browser = FakeSheetBrowser(results_always)
    report = render_game(golden_game(), tmp_path, browser)
    # A pass whose layout did not change prints nothing new, so the materials print at most once per pass.
    assert 1 < browser.calls.count("2 - PRINT THIS (game materials).pdf") <= MAX_PASSES
    assert report.findings
    assert {(finding.rule, finding.file) for finding in report.findings} == {("render.toolkit_overflow", None)}


def test_tightened_raises_the_level_of_each_overflowing_group() -> None:
    assert tightened({"results": 1, "notes": 2}, {"results", "hints"}) == {"results": 2, "notes": 2, "hints": 1}


def test_without_hints_the_render_skips_the_hints_file(tmp_path: Path) -> None:
    report = render_game(configured(golden_game(), assistance={"hints": False}), tmp_path, None)
    assert set(report.outputs) == {"manual", "materials", "solutions"}


def test_the_manual_comes_first_and_corner_codes_count_inside_each_stage() -> None:
    plans = output_plans(golden_game())
    assert [plan.id for plan in plans] == ["manual", "materials", "hints", "solutions"]
    assert plans[1].sheets[6].corner == "A · 2/4"


def test_sheet_source_files_point_document_sheets_to_their_file() -> None:
    plans = output_plans(golden_game())
    files = sheet_source_files(golden_game(), plans[1])
    assert files[:7] == [None, None, None, None, None, None, "documents/D1.md"]
