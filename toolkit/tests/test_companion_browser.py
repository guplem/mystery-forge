"""End-to-end test of the companion page: the golden game's page, opened from file:// in a real browser."""

import os
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Error, Page, Playwright, expect, sync_playwright
from test_assemble import FAKE_IMPLEMENTATIONS, GOLDEN_GAME

from mystery_forge.assemble import assemble_game
from mystery_forge.render.companion_data import build_companion_html

pytestmark = pytest.mark.browser

COMPANION_FILE_NAME: str = "Phone or computer companion.html"
CHROMIUM_CHANNELS: tuple[str | None, ...] = ("chrome", "msedge", None)
# A browser where every access to localStorage throws, like Safari with storage blocked.
BROKEN_STORAGE_SCRIPT: str = """
Object.defineProperty(window, 'localStorage', {
  configurable: true,
  get() { throw new DOMException('Storage is blocked.', 'SecurityError'); },
});
"""
LOCKED_PUZZLE_TITLE: str = "How did the thief reach the rock?"


@pytest.fixture(scope="module")
def companion_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    game_dir: Path = tmp_path_factory.mktemp("companion")
    shutil.copytree(GOLDEN_GAME / "source", game_dir / "source")
    game = assemble_game(game_dir, FAKE_IMPLEMENTATIONS).game
    assert game is not None
    page_file: Path = game_dir / COMPANION_FILE_NAME
    page_file.write_text(build_companion_html(game), encoding="utf-8")
    return page_file.as_uri()


@pytest.fixture(scope="module")
def playwright() -> Iterator[Playwright]:
    with sync_playwright() as running:
        yield running


def launch_chromium(playwright: Playwright) -> Browser:
    for channel in CHROMIUM_CHANNELS:
        try:
            return playwright.chromium.launch(channel=channel) if channel else playwright.chromium.launch()
        except Error:
            continue
    pytest.fail("No Chromium-based browser found. Install Chrome or Edge, or run `forge doctor --install-browser`.")


def launch_firefox(playwright: Playwright) -> Browser:
    try:
        return playwright.firefox.launch()
    except Error:
        if os.environ.get("MYSTERY_FORGE_REQUIRE_FIREFOX") == "1":
            raise
        pytest.skip("Playwright's Firefox is not installed (`uv run playwright install firefox`).")


def open_page(browser: Browser, url: str, init_script: str | None = None) -> tuple[Page, list[str]]:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    if init_script is not None:
        context.add_init_script(init_script)
    page: Page = context.new_page()
    errors: list[str] = []
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url)
    return page, errors


def check(page: Page, code: str | None, answer: str) -> None:
    """Check an answer; without a code, keep the puzzle that the page selected by itself."""
    page.click("[data-tab=check]")
    if code is not None:
        page.click(f"[data-puzzle={code}]")
    page.fill("#answer-input", answer)
    page.click("#answer-submit")


def assert_locked_titles_hidden(page: Page) -> None:
    for tab in ("start", "check", "hints", "solutions"):
        page.click(f"[data-tab={tab}]")
        assert LOCKED_PUZZLE_TITLE not in page.inner_text("body"), tab


def play_the_golden_game(page: Page) -> None:
    expect(page.locator("#intro")).to_contain_text("Gull Rock, the morning of 15 March 1931")
    expect(page.locator("[data-stage=B]")).to_contain_text("Sealed")
    assert "The boathouse box" not in page.inner_text("body")
    assert_locked_titles_hidden(page)

    check(page, "A1", "lighthouse")
    expect(page.locator("#answer-result")).to_have_attribute("data-result", "wrong")
    expect(page.locator("#answer-result")).to_contain_text("Not quite")
    check(page, "A1", "YXLXQEORPB")
    expect(page.locator("#answer-result")).to_have_attribute("data-result", "near")
    expect(page.locator("#answer-result")).to_contain_text("Count back, not forward.")
    check(page, "A1", " Boat-House ")
    expect(page.locator("#answer-result")).to_have_attribute("data-result", "correct")
    expect(page.locator("#unlock-call")).to_contain_text("Open now: Envelope B")
    expect(page.locator("[data-puzzle=B1]")).to_contain_text(LOCKED_PUZZLE_TITLE)
    page.click("[data-tab=start]")
    expect(page.locator("[data-stage=B]")).to_contain_text("The boathouse box")

    page.click("[data-tab=hints]")
    hints = page.locator("[data-hint-card=A2] .hint")
    expect(hints).to_have_count(0)
    page.click("[data-hint-button=A2]")
    expect(page.locator("#confirm-dialog")).to_contain_text("Show hint 1 for puzzle A2?")
    page.click("#confirm-no")
    expect(page.locator("#confirm-dialog")).to_have_count(0)
    expect(hints).to_have_count(0)
    page.click("[data-hint-button=A2]")
    page.click("#confirm-yes")
    expect(hints).to_have_count(1)
    expect(hints).to_contain_text("You need the logbook and the supply receipt.")
    expect(page.locator("[data-hint-button=A2]")).to_have_text("Show hint 2")
    for _level in (1, 2):
        page.click("[data-hint-button=B1]")
        page.click("#confirm-yes")
    expect(page.locator("[data-hint-card=B1] .hint")).to_have_count(2)
    expect(page.locator("[data-hint-button=B1]")).to_have_text("Show the answer")
    page.click("[data-hint-button=B1]")
    expect(page.locator("#confirm-dialog")).to_contain_text("This spoils the puzzle")
    expect(page.locator("[data-answer=B1]")).to_have_count(0)
    page.click("#confirm-yes")
    expect(page.locator("[data-answer=B1]")).to_contain_text("low tide")

    page.click("[data-tab=solutions]")
    expect(page.locator("#solutions-warning")).to_contain_text("Spoilers ahead")
    assert "0726" not in page.inner_text("body")
    page.click("#solutions-enter")
    assert "0726" not in page.inner_text("body")
    page.click("[data-solution-button=A2]")
    expect(page.locator("[data-solution-card=A2]")).to_contain_text("0726")
    expect(page.locator("[data-solution-card=A1]")).not_to_contain_text("boathouse")

    page.click("[data-tab=accuse]")
    page.click("#accuse-submit")
    expect(page.locator("#accuse-incomplete")).to_be_visible()
    page.check("input[name=question-who][value=felix]")
    page.check("input[name=question-why][value=prank]")
    page.click("#accuse-submit")
    page.click("#confirm-yes")
    expect(page.locator("#accuse-score")).to_have_text("50 of 75 points")
    expect(page.locator("#accuse-rank")).to_have_text("Close, but not quite")
    expect(page.locator("#accuse-result")).to_contain_text("How you could have known")

    page.click("[data-tab=start]")
    page.click("#timer-toggle")
    expect(page.locator("#timer-toggle")).to_have_text("Pause")


def assert_progress_survived(page: Page) -> None:
    page.reload()
    expect(page.locator("[data-stage=B]")).to_contain_text("Open")
    expect(page.locator("#timer-toggle")).to_have_text("Pause")
    page.click("[data-tab=hints]")
    expect(page.locator("[data-hint-card=A2] .hint")).to_have_count(1)
    page.click("[data-tab=accuse]")
    expect(page.locator("#accuse-rank")).to_have_text("Close, but not quite")


def run_smoke_test(launch: Callable[[Playwright], Browser], playwright: Playwright, url: str) -> None:
    browser: Browser = launch(playwright)
    try:
        page, errors = open_page(browser, url)
        play_the_golden_game(page)
        assert_progress_survived(page)
        assert errors == []

        blocked, blocked_errors = open_page(browser, url, BROKEN_STORAGE_SCRIPT)
        expect(blocked.locator("#storage-off")).to_be_visible()
        check(blocked, None, "boathouse")
        expect(blocked.locator("#unlock-call")).to_contain_text("Envelope B")
        expect(blocked.locator("[data-puzzle=A1]")).to_have_attribute("aria-pressed", "true")
        assert blocked_errors == []
    finally:
        browser.close()


def test_the_companion_works_from_a_file_in_chromium(playwright: Playwright, companion_url: str) -> None:
    run_smoke_test(launch_chromium, playwright, companion_url)


def test_the_companion_works_from_a_file_in_firefox(playwright: Playwright, companion_url: str) -> None:
    run_smoke_test(launch_firefox, playwright, companion_url)
