import pytest
from playwright.sync_api import Error as PlaywrightError

from mystery_forge.mechanics.base import RenderedArtifact
from mystery_forge.render.pdf import (
    NO_BROWSER_MESSAGE,
    ArtifactReading,
    BoxMeasurement,
    BrowserNotFoundError,
    PageProbe,
    SheetMeasurement,
    launch_first_available,
    overflow_findings,
    rendered_artifacts,
)


def box(**values: float) -> BoxMeasurement:
    sizes: dict[str, float] = {"scroll_height": 100, "client_height": 100, "scroll_width": 50, "client_width": 50}
    sizes.update(values)
    return BoxMeasurement(name="prop", **sizes)


def sheet(boxes: list[BoxMeasurement] | None = None, escaped: int = 0, scroll_height: float = 1000) -> SheetMeasurement:
    return SheetMeasurement(
        scroll_height=scroll_height,
        client_height=1000,
        scroll_width=700,
        client_width=700,
        boxes=boxes or [],
        escaped=escaped,
        text="",
    )


def test_launch_takes_the_first_channel_that_starts() -> None:
    tried: list[str | None] = []

    def launch(channel: str | None) -> str:
        tried.append(channel)
        if channel == "chrome":
            raise PlaywrightError("no chrome")
        return f"browser:{channel}"

    assert launch_first_available(launch) == "browser:msedge"
    assert tried == ["chrome", "msedge"]


def test_launch_fails_with_a_clear_message_when_nothing_starts() -> None:
    def launch(channel: str | None) -> str:
        raise PlaywrightError(f"no {channel}")

    with pytest.raises(BrowserNotFoundError, match="Install Chrome or Edge"):
        launch_first_available(launch)
    assert "playwright install chromium" in NO_BROWSER_MESSAGE


def test_a_box_overflows_by_scroll_size_or_by_content_in_its_padding() -> None:
    assert not box().overflows
    assert not box(scroll_height=101).overflows
    assert box(scroll_height=102).overflows
    assert box(scroll_width=52).overflows
    assert not box(overflow_bottom=3).overflows
    assert box(overflow_bottom=4).overflows
    assert box(overflow_right=4).overflows


def test_overflow_findings_name_the_sheet_and_its_source_file() -> None:
    probe = PageProbe(
        sheets=[sheet(), sheet(scroll_height=1200), sheet(boxes=[box(overflow_bottom=30)]), sheet(escaped=2)],
        artifacts=[],
    )
    findings = overflow_findings(probe, "materials.html", [None, "documents/D2.md", None])
    assert [finding.rule for finding in findings] == ["render.overflow"] * 3
    assert [finding.file for finding in findings] == ["documents/D2.md", "materials.html", "materials.html"]
    assert findings[0].path == "materials.html sheet 2"
    assert "the box 'sheet' overflows" in findings[0].message
    assert "the box 'prop' overflows" in findings[1].message
    assert "2 element(s) reach outside the sheet" in findings[2].message
    assert findings[0].fix_hint is not None and "pagebreak" in findings[0].fix_hint


def test_rendered_artifacts_keep_the_first_copy_of_each_puzzle() -> None:
    probe = PageProbe(
        sheets=[],
        artifacts=[
            ArtifactReading(puzzle="P1", text="one", html="<b>one</b>"),
            ArtifactReading(puzzle="P1", text="copy", html="copy"),
            ArtifactReading(puzzle="P2", text="", html="<svg></svg>"),
        ],
    )
    assert rendered_artifacts(probe) == {
        "P1": RenderedArtifact(text="one", html="<b>one</b>"),
        "P2": RenderedArtifact(text="", html="<svg></svg>"),
    }
