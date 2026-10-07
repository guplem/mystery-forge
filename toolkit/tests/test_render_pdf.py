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
    describe_element,
    launch_first_available,
    overflow_findings,
    overflowing_sheets,
    rendered_artifacts,
)


def box(bottom_element: str = "", right_element: str = "", **values: float) -> BoxMeasurement:
    sizes: dict[str, float] = {"scroll_height": 100, "client_height": 100, "scroll_width": 50, "client_width": 50}
    sizes.update(values)
    return BoxMeasurement(name="prop", bottom_element=bottom_element, right_element=right_element, **sizes)


def sheet(
    boxes: list[BoxMeasurement] | None = None,
    escaped: int = 0,
    scroll_height: float = 1000,
    escaped_element: str = "",
) -> SheetMeasurement:
    return SheetMeasurement(
        scroll_height=scroll_height,
        client_height=1000,
        scroll_width=700,
        client_width=700,
        boxes=boxes or [],
        escaped=escaped,
        escaped_distance=12.4,
        escaped_element=escaped_element,
        escaped_edge="right",
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


def test_document_overflow_goes_to_the_writer_and_toolkit_overflow_to_nobody() -> None:
    probe = PageProbe(
        sheets=[sheet(), sheet(scroll_height=1200), sheet(boxes=[box(overflow_bottom=30)]), sheet(escaped=2)],
        artifacts=[],
    )
    assert overflowing_sheets(probe) == [
        (1, ["the sheet: content 200 px too tall"]),
        (2, ["the box 'prop': the content reaches 30 px past the bottom edge"]),
        (3, ["2 element(s) reach outside the sheet"]),
    ]
    findings = overflow_findings(probe, "materials.html", [None, "documents/D2.md", None])
    assert [(finding.rule, finding.file) for finding in findings] == [
        ("render.overflow", "documents/D2.md"),
        ("render.toolkit_overflow", None),
        ("render.toolkit_overflow", None),
    ]
    assert findings[0].path == "materials.html sheet 2"
    assert findings[0].fix_hint is not None and "pagebreak" in findings[0].fix_hint
    assert findings[1].fix_hint is not None and "toolkit bug" in findings[1].fix_hint
    assert "2 element(s) reach outside the sheet" in findings[2].message


def test_an_overflow_says_how_much_and_what_overflows() -> None:
    tall = box(bottom_element="div.mf-handwriting", scroll_height=220)
    wide = box(right_element="p", scroll_width=60, overflow_right=7.2)
    reaching = box(bottom_element="div.safe.doc-area", right_element="div.mf-handwriting", overflow_right=7.4)
    probe = PageProbe(sheets=[sheet(boxes=[tall, wide, reaching], escaped=1, escaped_element="span")], artifacts=[])
    assert overflowing_sheets(probe) == [
        (
            0,
            [
                "the box 'prop': content 120 px too tall; the first part past the edge is a handwriting block",
                "the box 'prop': content 10 px too wide; the first part past the edge is a <p> element",
                "the box 'prop': a handwriting block reaches 7 px past the right edge",
                "1 element(s) reach outside the sheet; the farthest, a <span> element, reaches 12 px past the "
                "right edge",
            ],
        )
    ]


def test_describe_element_names_the_part_that_a_fixer_must_shorten() -> None:
    assert describe_element("div.mf-handwriting.big") == "a handwriting block"
    assert describe_element("div.police-report") == "a police report block"
    assert describe_element("p") == "a <p> element"
    assert describe_element("") == "the content"


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
