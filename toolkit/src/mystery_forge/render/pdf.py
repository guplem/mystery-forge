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
# Content may reach this far into a box's padding: a rotated stamp or a handwriting line grows its bounding box a bit.
CONTENT_TOLERANCE: Final[float] = 3.0
# The boxes with a fixed size: the safe area of each sheet, the full-page papers, and every element marked `fit`.
FIXED_BOXES: Final[str] = ".safe, .prop-full, .fit"

MEASURE_SCRIPT: Final[str] = """
(selector) => {
  const inFlowEdges = (box) => {
    let bottom = -Infinity;
    let right = -Infinity;
    const walk = (element) => {
      for (const child of element.children) {
        const style = getComputedStyle(child);
        if (style.position === 'absolute' || style.position === 'fixed' || style.display === 'none') continue;
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
  return Array.from(document.querySelectorAll('section.sheet')).map((sheet) => {
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
      };
    });
    let escaped = 0;
    for (const element of sheet.querySelectorAll('*')) {
      const rect = element.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;
      if (rect.left < frame.left - 1 || rect.top < frame.top - 1 || rect.right > frame.right + 1
          || rect.bottom > frame.bottom + 1) escaped += 1;
    }
    return {
      boxes: boxes, escaped: escaped, text: sheet.innerText,
      scroll_height: sheet.scrollHeight, client_height: sheet.clientHeight,
      scroll_width: sheet.scrollWidth, client_width: sheet.clientWidth,
    };
  });
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

    @property
    def overflows(self) -> bool:
        return (
            self.scroll_height > self.client_height + OVERFLOW_TOLERANCE
            or self.scroll_width > self.client_width + OVERFLOW_TOLERANCE
            or self.overflow_bottom > CONTENT_TOLERANCE
            or self.overflow_right > CONTENT_TOLERANCE
        )


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


def sheet_overflow_problems(sheet: SheetMeasurement) -> list[str]:
    problems: list[str] = []
    whole = BoxMeasurement(
        name="sheet",
        scroll_height=sheet.scroll_height,
        client_height=sheet.client_height,
        scroll_width=sheet.scroll_width,
        client_width=sheet.client_width,
    )
    problems.extend(f"the box '{box.name}' overflows" for box in (whole, *sheet.boxes) if box.overflows)
    if sheet.escaped:
        problems.append(f"{sheet.escaped} element(s) reach outside the sheet")
    return problems


def overflow_findings(probe: PageProbe, output_file: str, sheet_files: list[str | None]) -> list[Finding]:
    """One `render.overflow` finding per sheet whose content does not fit. `sheet_files` names each sheet's source."""
    findings: list[Finding] = []
    for index, sheet in enumerate(probe.sheets):
        problems: list[str] = sheet_overflow_problems(sheet)
        if problems:
            source: str | None = sheet_files[index] if index < len(sheet_files) else None
            findings.append(
                Finding(
                    severity="error",
                    rule="render.overflow",
                    message=f"Sheet {index + 1} of {output_file} does not fit its page: {'; '.join(problems)}.",
                    file=source or output_file,
                    path=f"{output_file} sheet {index + 1}",
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
