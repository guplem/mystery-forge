from pathlib import Path

from test_render_support import configured, golden_game

from mystery_forge.render.game_renderer import output_plans, render_game, sheet_source_files
from mystery_forge.render.pdf import ArtifactReading, BoxMeasurement, PageProbe, SheetMeasurement


class FakeSheetBrowser:
    """Measure every sheet as fitting, except the sheets in `overflowing`, and write nothing."""

    def __init__(self, overflowing: frozenset[int] = frozenset()) -> None:
        self.overflowing: frozenset[int] = overflowing
        self.calls: list[tuple[Path, int]] = []

    def print_output(self, html: str, pdf_path: Path, preview_paths: list[Path]) -> PageProbe:
        self.calls.append((pdf_path, len(preview_paths)))
        count: int = html.count('<section class="sheet ')
        sheets = [
            SheetMeasurement(
                scroll_height=1200 if index in self.overflowing else 1100,
                client_height=1100,
                scroll_width=800,
                client_width=800,
                boxes=[BoxMeasurement(name="safe", scroll_height=1, client_height=1, scroll_width=1, client_width=1)],
                escaped=0,
                text=f"sheet {index}",
            )
            for index in range(count)
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
    browser = FakeSheetBrowser(overflowing=frozenset({6}))
    report = render_game(golden_game(), tmp_path, browser, "noir")
    assert report.theme == "noir"
    assert [call[0].name for call in browser.calls] == [
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
    files = [finding.file for finding in report.findings]
    assert "documents/D1.md" in files
    assert "solutions.html" in files


def test_without_hints_the_render_skips_the_hints_file(tmp_path: Path) -> None:
    report = render_game(configured(golden_game(), assistance={"hints": False}), tmp_path, None)
    assert set(report.outputs) == {"manual", "materials", "solutions"}


def test_the_manual_lists_the_sheet_count_of_the_other_outputs() -> None:
    plans = output_plans(golden_game())
    assert [plan.id for plan in plans] == ["manual", "materials", "hints", "solutions"]
    assert plans[1].sheets[6].corner == "A · 2/4"


def test_sheet_source_files_point_document_sheets_to_their_file() -> None:
    plans = output_plans(golden_game())
    files = sheet_source_files(golden_game(), plans[1])
    assert files[:7] == [None, None, None, None, None, None, "documents/D1.md"]
