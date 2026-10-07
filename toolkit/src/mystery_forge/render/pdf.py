"""The browser layer: print an output HTML file to PDF with Playwright, and measure what the browser drew.

This layer stays thin. The page scripts below only collect raw facts (sizes, visible text, artifact HTML), and pure
functions decide what those facts mean, so the unit tests cover every decision without a browser. Playwright uses
the installed Chrome, then Edge, then its own Chromium, and never downloads a browser (`adr/0005-rendering-stack.md`).
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final, Protocol

from playwright.sync_api import Browser, sync_playwright
from playwright.sync_api import Error as PlaywrightError
from pydantic import BaseModel, ConfigDict

from mystery_forge.findings import Finding
from mystery_forge.mechanics.base import RenderedArtifact

BROWSER_CHANNELS: Final[tuple[str | None, ...]] = ("chrome", "msedge", None)
NO_BROWSER_MESSAGE: Final[str] = (
    "No Chromium-based browser could start. Install Chrome or Edge, or run `uv run playwright install chromium`."
)
# Thumbnails for the visual review: about a third of the printed size.
PREVIEW_SCALE: Final[float] = 0.35
# A box overflows when its content is taller or wider than the box by more than this many CSS pixels.
OVERFLOW_TOLERANCE: Final[float] = 1.0
# Content may reach this far into a box's padding before it counts as an overflow.
CONTENT_TOLERANCE: Final[float] = 3.0
# The boxes with a fixed size: the safe area of each sheet, the full-page papers, and every element marked `fit`.
FIXED_BOXES: Final[str] = ".safe, .prop-full, .fit"

# The script measures layout boxes without CSS rotations: a handwriting block turned by 1 degree fits its box, but its
# rotated bounding box reaches a few pixels past the edge. While the script measures, an identity transform replaces
# each rotation, so that an element stays the containing block of its absolute children.
MEASURE_SCRIPT: Final[str] = """
(selector) => {
  const flattened = [];
  for (const element of document.querySelectorAll('section.sheet *')) {
    if (!(element instanceof HTMLElement) || getComputedStyle(element).transform === 'none') continue;
    const style = element.style;
    flattened.push([element, style.getPropertyValue('transform'), style.getPropertyPriority('transform')]);
    style.setProperty('transform', 'translate(0px, 0px)', 'important');
  }
  const describe = (element) => [element.tagName.toLowerCase(), ...Array.from(element.classList)].join('.');
  const inFlow = (element) => {
    const style = getComputedStyle(element);
    return style.position !== 'absolute' && style.position !== 'fixed' && style.display !== 'none';
  };
  const inFlowEdges = (box) => {
    let bottom = -Infinity;
    let right = -Infinity;
    const walk = (element) => {
      for (const child of element.children) {
        if (!inFlow(child)) continue;
        const rect = child.getBoundingClientRect();
        if (rect.width > 0 || rect.height > 0) {
          bottom = Math.max(bottom, rect.bottom);
          right = Math.max(right, rect.right);
        }
        walk(child);
      }
    };
    walk(box);
    return [bottom, right];
  };
  // The first element that reaches past an edge, followed down to its deepest part with a class: the block to shorten.
  const firstPast = (box, isPast) => {
    let found = '';
    let level = box;
    while (level) {
      const next = Array.from(level.children).find((child) => inFlow(child) && isPast(child.getBoundingClientRect()));
      if (next && next.classList.length) found = describe(next);
      level = next;
    }
    return found;
  };
  const measureSheet = (sheet) => {
    const frame = sheet.getBoundingClientRect();
    const boxes = Array.from(sheet.querySelectorAll(selector)).map((element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      const [bottom, right] = inFlowEdges(element);
      const contentBottom = rect.bottom - parseFloat(style.paddingBottom) - parseFloat(style.borderBottomWidth);
      const contentRight = rect.right - parseFloat(style.paddingRight) - parseFloat(style.borderRightWidth);
      return {
        name: element.className.toString(),
        scroll_height: element.scrollHeight, client_height: element.clientHeight,
        scroll_width: element.scrollWidth, client_width: element.clientWidth,
        overflow_bottom: Math.max(0, bottom - contentBottom), overflow_right: Math.max(0, right - contentRight),
        bottom_element: firstPast(element, (box) => box.bottom > contentBottom + 1),
        right_element: firstPast(element, (box) => box.right > contentRight + 1),
      };
    });
    const escape = {count: 0, distance: 0, element: '', edge: ''};
    for (const element of sheet.querySelectorAll('*')) {
      const rect = element.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;
      const reach = [
        ['left', frame.left - rect.left], ['top', frame.top - rect.top],
        ['right', rect.right - frame.right], ['bottom', rect.bottom - frame.bottom],
      ];
      const [edge, distance] = reach.reduce((farthest, entry) => (entry[1] > farthest[1] ? entry : farthest));
      if (distance <= 1) continue;
      escape.count += 1;
      if (distance > escape.distance) Object.assign(escape, {distance, element: describe(element), edge});
    }
    return {
      boxes: boxes, text: sheet.innerText,
      escaped: escape.count, escaped_distance: escape.distance, escaped_element: escape.element,
      escaped_edge: escape.edge,
      scroll_height: sheet.scrollHeight, client_height: sheet.clientHeight,
      scroll_width: sheet.scrollWidth, client_width: sheet.clientWidth,
    };
  };
  try {
    return Array.from(document.querySelectorAll('section.sheet')).map(measureSheet);
  } finally {
    for (const [element, value, priority] of flattened) {
      element.style.removeProperty('transform');
      if (value) element.style.setProperty('transform', value, priority);
    }
  }
}
"""
ARTIFACT_SCRIPT: Final[str] = """
() => Array.from(document.querySelectorAll('[data-artifact]')).map((element) => ({
  puzzle: element.dataset.artifact, text: element.innerText, html: element.innerHTML,
}))
"""


class BoxMeasurement(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    scroll_height: float
    client_height: float
    scroll_width: float
    client_width: float
    # How far the in-flow content reaches past the box's content edge (inside its padding), in CSS pixels.
    overflow_bottom: float = 0
    overflow_right: float = 0
    # The first element that reaches past the bottom edge and past the right edge, as "tag.class.class".
    bottom_element: str = ""
    right_element: str = ""

    def problems(self) -> list[str]:
        """What overflows and by how much, so that a fixer knows what to shorten."""
        found: list[str] = []
        taller: float = self.scroll_height - self.client_height
        if taller > OVERFLOW_TOLERANCE:
            found.append(f"content {round(taller)} px too tall{part_named(self.bottom_element)}")
        elif self.overflow_bottom > CONTENT_TOLERANCE:
            found.append(
                f"{describe_element(self.bottom_element)} reaches {round(self.overflow_bottom)} px past the bottom edge"
            )
        wider: float = self.scroll_width - self.client_width
        if wider > OVERFLOW_TOLERANCE:
            found.append(f"content {round(wider)} px too wide{part_named(self.right_element)}")
        elif self.overflow_right > CONTENT_TOLERANCE:
            found.append(
                f"{describe_element(self.right_element)} reaches {round(self.overflow_right)} px past the right edge"
            )
        return found

    @property
    def overflows(self) -> bool:
        return bool(self.problems())


class SheetMeasurement(BaseModel):
    """What the browser measured on one sheet: the sheet box, its fixed boxes, the elements outside it, its text."""

    model_config = ConfigDict(frozen=True)

    scroll_height: float
    client_height: float
    scroll_width: float
    client_width: float
    boxes: list[BoxMeasurement]
    escaped: int
    text: str
    # The element that reaches farthest outside the sheet: how far, which element, and past which edge.
    escaped_distance: float = 0
    escaped_element: str = ""
    escaped_edge: str = ""


class ArtifactReading(BaseModel):
    model_config = ConfigDict(frozen=True)

    puzzle: str
    text: str
    html: str


class PageProbe(BaseModel):
    model_config = ConfigDict(frozen=True)

    sheets: list[SheetMeasurement]
    artifacts: list[ArtifactReading]


class SheetBrowser(Protocol):
    """Print one output: write the PDF and one preview image per sheet, and return what the browser measured."""

    def print_output(self, html: str, pdf_path: Path, preview_paths: list[Path]) -> PageProbe: ...


class BrowserNotFoundError(RuntimeError):
    pass


def launch_first_available[BrowserType](launch: Callable[[str | None], BrowserType]) -> BrowserType:
    """Start the first browser channel that works: Chrome, then Edge, then Playwright's own Chromium."""
    for channel in BROWSER_CHANNELS:
        try:
            return launch(channel)
        except PlaywrightError:
            continue
    raise BrowserNotFoundError(NO_BROWSER_MESSAGE)


def describe_element(raw: str) -> str:
    """Name an element for a fixer: "div.mf-handwriting" is "a handwriting block", "p" is "a <p> element"."""
    if not raw:
        return "the content"
    tag, _, classes = raw.partition(".")
    first_class: str = classes.split(".")[0]
    if not first_class:
        return f"a <{tag}> element"
    return f"a {first_class.removeprefix('mf-').replace('-', ' ')} block"


def part_named(raw: str) -> str:
    return f"; the first part past the edge is {describe_element(raw)}" if raw else ""


def sheet_overflow_problems(sheet: SheetMeasurement) -> list[str]:
    whole = BoxMeasurement(
        name="sheet",
        scroll_height=sheet.scroll_height,
        client_height=sheet.client_height,
        scroll_width=sheet.scroll_width,
        client_width=sheet.client_width,
    )
    problems: list[str] = [f"the sheet: {problem}" for problem in whole.problems()]
    problems.extend(f"the box '{box.name}': {problem}" for box in sheet.boxes for problem in box.problems())
    if sheet.escaped:
        farthest: str = (
            f"; the farthest, {describe_element(sheet.escaped_element)}, reaches {round(sheet.escaped_distance)} px "
            f"past the {sheet.escaped_edge} edge"
            if sheet.escaped_element
            else ""
        )
        problems.append(f"{sheet.escaped} element(s) reach outside the sheet{farthest}")
    return problems


def overflowing_sheets(probe: PageProbe) -> list[tuple[int, list[str]]]:
    """The index and the problems of each sheet whose content does not fit."""
    measured = ((index, sheet_overflow_problems(sheet)) for index, sheet in enumerate(probe.sheets))
    return [(index, problems) for index, problems in measured if problems]


def overflow_findings(probe: PageProbe, output_file: str, sheet_files: list[str | None]) -> list[Finding]:
    """One finding per sheet whose content does not fit. `sheet_files` names the document file of each sheet.

    A document sheet gets `render.overflow` on its document file, because the game writer can shorten or split it.
    The toolkit builds every other sheet from game data, so its overflow is a toolkit bug: it gets
    `render.toolkit_overflow` with no file, which the fix groups never send to a game writer.
    """
    findings: list[Finding] = []
    for index, problems in overflowing_sheets(probe):
        source: str | None = sheet_files[index] if index < len(sheet_files) else None
        message: str = f"Sheet {index + 1} of {output_file} does not fit its page: {'; '.join(problems)}."
        path: str = f"{output_file} sheet {index + 1}"
        if source is None:
            findings.append(
                Finding(
                    severity="error",
                    rule="render.toolkit_overflow",
                    message=message,
                    path=path,
                    fix_hint="The toolkit builds this page. Report it as a toolkit bug; the game files cannot fix it.",
                )
            )
            continue
        findings.append(
            Finding(
                severity="error",
                rule="render.overflow",
                message=message,
                file=source,
                path=path,
                fix_hint="Shorten the text, or split the document with a `::: pagebreak` directive.",
            )
        )
    return findings


def rendered_artifacts(probe: PageProbe) -> dict[str, RenderedArtifact]:
    """The first rendered copy of each artifact, by puzzle id."""
    artifacts: dict[str, RenderedArtifact] = {}
    for reading in probe.artifacts:
        artifacts.setdefault(reading.puzzle, RenderedArtifact(text=reading.text, html=reading.html))
    return artifacts


class PlaywrightSheetBrowser:
    """The real `SheetBrowser`. The browser tests cover it; the unit tests use a fake."""

    def __init__(self, browser: Browser) -> None:
        self.browser: Browser = browser

    def print_output(self, html: str, pdf_path: Path, preview_paths: list[Path]) -> PageProbe:
        page = self.browser.new_page(device_scale_factor=PREVIEW_SCALE)
        try:
            page.set_content(html, wait_until="load")
            page.emulate_media(media="print")
            page.evaluate("document.fonts.ready.then(() => true)")
            probe = PageProbe(
                sheets=page.evaluate(MEASURE_SCRIPT, FIXED_BOXES), artifacts=page.evaluate(ARTIFACT_SCRIPT)
            )
            for sheet, preview_path in zip(page.locator("section.sheet").all(), preview_paths, strict=False):
                sheet.screenshot(path=preview_path, animations="disabled")
            page.pdf(path=pdf_path, prefer_css_page_size=True, print_background=True)
            return probe
        finally:
            page.close()


@contextmanager
def open_sheet_browser() -> Iterator[PlaywrightSheetBrowser]:
    """Start Playwright and a browser for one render. Raise `BrowserNotFoundError` when no browser starts."""
    with sync_playwright() as playwright:
        browser: Browser = launch_first_available(lambda channel: playwright.chromium.launch(channel=channel))
        try:
            yield PlaywrightSheetBrowser(browser)
        finally:
            browser.close()
