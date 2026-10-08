"""End-to-end tests of the configurator page, opened from file:// the way a user opens it with a double-click.

Chromium runs with the system Chrome, else Edge, else Playwright's own Chromium. Firefox runs when Playwright's
Firefox is installed. When it is missing the Firefox tests skip, unless MYSTERY_FORGE_REQUIRE_FIREFOX=1 (set it in CI).
"""

import json
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Browser, ConsoleMessage, FilePayload, Page, Playwright, ViewportSize, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from mystery_forge.config import normalize_config

pytestmark = pytest.mark.browser

PAGE_URL: str = (Path(__file__).resolve().parents[2] / "configurator" / "index.html").as_uri()
BROWSER_NAMES: list[str] = ["chromium", "firefox"]
CHROMIUM_CHANNELS: list[str | None] = ["chrome", "msedge", None]
THROWING_STORAGE_SCRIPT: str = """
for (const method of ['getItem', 'setItem', 'removeItem', 'clear', 'key']) {
  Storage.prototype[method] = function () {
    throw new DOMException('Storage is blocked.', 'SecurityError');
  };
}
"""


@dataclass
class OpenedPage:
    """The page, its browser name, and every console error or uncaught exception that it logged."""

    page: Page
    browser_name: str
    errors: list[str] = field(default_factory=list)


@pytest.fixture(scope="module")
def playwright_instance() -> Iterator[Playwright]:
    with sync_playwright() as playwright:
        yield playwright


def launch_chromium(playwright: Playwright) -> Browser:
    last_error: PlaywrightError | None = None
    for channel in CHROMIUM_CHANNELS:
        try:
            return playwright.chromium.launch(channel=channel)
        except PlaywrightError as error:
            last_error = error
    pytest.fail(f"No Chromium-based browser could start: {last_error}")


def launch_firefox(playwright: Playwright) -> Browser:
    try:
        return playwright.firefox.launch()
    except PlaywrightError as error:
        if os.environ.get("MYSTERY_FORGE_REQUIRE_FIREFOX") == "1":
            pytest.fail(f"Firefox is required but could not start: {error}")
        pytest.skip("Playwright's Firefox is not installed. Run: uv run playwright install firefox")


@pytest.fixture(scope="module", params=BROWSER_NAMES)
def browser(request: pytest.FixtureRequest, playwright_instance: Playwright) -> Iterator[Browser]:
    launched: Browser = (
        launch_chromium(playwright_instance) if request.param == "chromium" else launch_firefox(playwright_instance)
    )
    yield launched
    launched.close()


def open_page(
    browser: Browser, locale: str = "en-US", init_script: str = "", viewport: ViewportSize | None = None
) -> OpenedPage:
    context = browser.new_context(accept_downloads=True, locale=locale, viewport=viewport)
    if init_script:
        context.add_init_script(init_script)
    page: Page = context.new_page()
    opened = OpenedPage(page=page, browser_name=browser.browser_type.name)

    def record_console(message: ConsoleMessage) -> None:
        if message.type == "error":
            opened.errors.append(message.text)

    page.on("console", record_console)
    page.on("pageerror", lambda error: opened.errors.append(str(error)))
    page.goto(PAGE_URL)
    page.wait_for_selector("#section-players")
    return opened


@pytest.fixture
def opened(browser: Browser) -> Iterator[OpenedPage]:
    result: OpenedPage = open_page(browser)
    yield result
    result.page.context.close()


def estimate_value(page: Page, estimate_id: str) -> str:
    return page.inner_text(f'[data-estimate-id="{estimate_id}"] dd').strip()


def json_file(name: str, content: bytes) -> FilePayload:
    return FilePayload(name=name, mimeType="application/json", buffer=content)


def download_config(page: Page) -> dict[str, Any]:
    with page.expect_download() as download_info:
        page.click("#download-config")
    download = download_info.value
    assert download.suggested_filename.endswith(".mystery-config.json")
    downloaded: dict[str, Any] = json.loads(Path(download.path()).read_text(encoding="utf-8"))
    return downloaded


def test_the_page_loads_in_english_with_no_console_error(opened: OpenedPage) -> None:
    page: Page = opened.page
    assert page.inner_text("#section-players-title") == "Who is playing"
    assert page.get_attribute("html", "lang") == "en"
    assert page.is_checked("#input-audience-family")
    assert page.input_value("#input-players-count") == "4"
    assert page.inner_text('[data-estimate-id="play_time"] dd') == "1 h 30 min"
    assert opened.errors == []


def test_the_language_switch_changes_the_labels(opened: OpenedPage) -> None:
    page: Page = opened.page
    assert not page.is_visible("#language-note")
    page.click('[data-ui-language="es"]')
    assert page.inner_text("#section-players-title") == "Quién juega"
    assert page.inner_text("#download-config") == "Descargar configuración"
    assert page.get_attribute("html", "lang") == "es"
    assert page.get_attribute('[data-ui-language="es"]', "aria-pressed") == "true"
    page.click('[data-ui-language="ca"]')
    assert page.inner_text("#section-players-title") == "Qui juga"
    assert page.get_attribute("html", "lang") == "ca"
    assert page.get_attribute('[data-ui-language="ca"]', "aria-pressed") == "true"
    assert page.get_attribute('[data-ui-language="es"]', "aria-pressed") == "false"
    page.click('[data-ui-language="en"]')
    assert page.inner_text("#section-players-title") == "Who is playing"
    assert opened.errors == []


def test_the_game_language_and_the_paper_follow_the_page_language(opened: OpenedPage) -> None:
    page: Page = opened.page
    assert page.is_checked("#input-equipment-paper-Letter")
    page.click('[data-ui-language="es"]')
    assert page.input_value("#input-language") == "es"
    assert page.is_checked("#input-equipment-paper-A4")
    assert page.is_visible("#language-note")
    assert "Idioma del juego: Español. Papel: A4." in page.inner_text("#language-note")
    page.click('[data-ui-language="en"]')
    assert page.input_value("#input-language") == "en"
    assert page.is_checked("#input-equipment-paper-Letter")
    page.select_option("#input-language", "de")
    assert not page.is_visible("#language-note")


def test_a_game_language_that_the_user_chose_stays(opened: OpenedPage) -> None:
    page: Page = opened.page
    page.select_option("#input-language", "fr")
    page.click('[data-ui-language="es"]')
    assert page.input_value("#input-language") == "fr"
    assert page.is_checked("#input-equipment-paper-Letter")
    assert not page.is_visible("#language-note")


def test_the_expert_options_are_folded(opened: OpenedPage) -> None:
    page: Page = opened.page
    assert not page.is_visible("#input-generation-quality-best")
    assert not page.is_visible("#input-generation-seed")
    page.click("#advanced-generation > summary")
    assert page.is_visible("#input-generation-seed")
    assert "about" in page.inner_text('[data-quality-time="best"]')


def test_the_next_steps_show_before_the_download(opened: OpenedPage) -> None:
    page: Page = opened.page
    next_steps: str = page.inner_text("#next-steps")
    assert page.is_visible("#next-steps")
    assert "create a game" in next_steps
    assert "Windows:" in next_steps
    assert "macOS:" in next_steps
    assert page.get_attribute("#next-steps a >> nth=0", "href") == (
        "https://docs.astral.sh/uv/getting-started/installation/"
    )
    assert page.get_attribute("#next-steps a >> nth=1", "href") == "https://claude.com/claude-code"
    assert not page.is_visible("#copy-prompt")


def count_text_lines(page: Page, selector: str) -> int:
    lines: int = page.evaluate(
        """(selector) => {
          const range = document.createRange();
          range.selectNodeContents(document.querySelector(selector));
          return new Set([...range.getClientRects()].map((rect) => Math.round(rect.top))).size;
        }""",
        selector,
    )
    return lines


@pytest.mark.parametrize("viewport", [ViewportSize(width=1366, height=900), ViewportSize(width=390, height=844)])
@pytest.mark.parametrize(("locale", "puzzles_word"), [("es-ES", "enigmas"), ("ca-ES", "enigmes")])
def test_the_spanish_and_catalan_actions_fit_on_one_line(
    browser: Browser, viewport: ViewportSize, locale: str, puzzles_word: str
) -> None:
    opened = open_page(browser, locale=locale, viewport=viewport)
    try:
        page: Page = opened.page
        page.click("#prompt-panel > summary")
        for selector in ("#download-config span", ".file-button span", "#reset-config span", "#copy-prompt span"):
            assert count_text_lines(page, selector) == 1, selector
        assert re.fullmatch(rf"\d+ {puzzles_word} · 1 h 30 min", page.inner_text("#mobile-summary-numbers"))
    finally:
        opened.page.context.close()


def test_a_spanish_browser_opens_the_page_in_spanish_with_a4_paper(browser: Browser) -> None:
    spanish = open_page(browser, locale="es-ES")
    try:
        assert spanish.page.inner_text("#section-players-title") == "Quién juega"
        assert spanish.page.is_checked("#input-equipment-paper-A4")
        assert spanish.page.input_value("#input-language") == "es"
    finally:
        spanish.page.context.close()


def test_a_catalan_browser_opens_the_page_in_catalan_with_a4_paper(browser: Browser) -> None:
    catalan = open_page(browser, locale="ca-ES")
    try:
        assert catalan.page.inner_text("#section-players-title") == "Qui juga"
        assert catalan.page.get_attribute("html", "lang") == "ca"
        assert catalan.page.is_checked("#input-equipment-paper-A4")
        assert catalan.page.input_value("#input-language") == "ca"
    finally:
        catalan.page.context.close()


def test_an_audience_preset_updates_the_fields(opened: OpenedPage) -> None:
    page: Page = opened.page
    assert page.is_checked("#input-content-death_allowed")
    page.check("#input-audience-kids")
    assert page.is_checked("#input-difficulty-easy")
    assert page.is_checked("#input-content-scary_level-none")
    assert page.is_checked("#input-visuals-style-kids")
    assert page.is_checked("#input-visuals-readable_font")
    assert not page.is_checked("#input-content-death_allowed")
    assert "Kids" in page.inner_text("#status-message")


def test_a_warning_appears_for_a_bad_combination(opened: OpenedPage) -> None:
    page: Page = opened.page
    page.check("#input-audience-kids")
    assert page.locator('[data-warning-id="kids_death"]').count() == 0
    page.check("#input-content-death_allowed")
    assert page.locator('[data-warning-id="kids_death"]').count() == 1


def test_the_story_idea_shows_its_character_limit(opened: OpenedPage) -> None:
    page: Page = opened.page
    assert page.inner_text("#count-theme-idea") == "0 of 5000 characters"
    page.fill("#input-theme-idea", "A stolen violin")
    assert page.inner_text("#count-theme-idea") == "15 of 5000 characters"


def test_the_estimate_follows_the_players_and_the_duration(opened: OpenedPage) -> None:
    page: Page = opened.page
    puzzles_for_four: int = int(estimate_value(page, "puzzles"))
    page.click('#field-players-count [data-step="1"]')
    page.click('#field-players-count [data-step="1"]')
    assert page.input_value("#input-players-count") == "6"
    puzzles_for_six: int = int(estimate_value(page, "puzzles"))
    assert puzzles_for_six > puzzles_for_four
    page.fill("#input-duration_minutes", "60")
    assert estimate_value(page, "play_time") == "1 h"
    assert int(estimate_value(page, "puzzles")) < puzzles_for_six


def test_download_gives_a_config_that_the_toolkit_accepts(opened: OpenedPage) -> None:
    page: Page = opened.page
    page.check("#input-audience-adults")
    page.click('#field-players-count [data-step="1"]')
    page.fill("#input-theme-idea", "A stolen violin on the night train")
    page.fill("#input-players-names", "Ana")
    page.press("#input-players-names", "Enter")
    page.check("#input-equipment-printer-black_and_white")
    page.uncheck("#input-equipment-scissors")
    page.check("#input-puzzle_preferences-logic-like")
    downloaded: dict[str, Any] = download_config(page)

    result = normalize_config(downloaded)
    assert result.findings == []
    assert result.config is not None
    assert downloaded["audience"] == "adults"
    assert downloaded["difficulty"] == "hard"
    assert downloaded["players"] == {"count": 5, "names": ["Ana"]}
    assert downloaded["theme"]["idea"] == "A stolen violin on the night train"
    assert downloaded["equipment"]["printer"] == "black_and_white"
    assert downloaded["equipment"]["scissors"] is False
    assert downloaded["equipment"]["paper"] == "Letter"
    assert downloaded["puzzle_preferences"]["logic"] == "like"
    assert page.is_visible("#next-steps")
    assert "mystery-forge-a-stolen-violin-on-the-night-train.mystery-config.json" in page.inner_text("#next-steps")
    assert opened.errors == []


def test_loading_a_config_file_restores_the_form(opened: OpenedPage) -> None:
    page: Page = opened.page
    config: dict[str, Any] = {
        "schema_version": 1,
        "audience": "teens",
        "players": {"count": 9, "names": ["Leo", "Mia"]},
        "difficulty": "expert",
        "theme": {"idea": "Ghost in the lighthouse", "tone": "spooky"},
        "visuals": {"style": "noir"},
    }
    page.set_input_files(
        "#config-file-input", files=[json_file("saved.mystery-config.json", json.dumps(config).encode())]
    )
    page.wait_for_function("document.querySelector('#input-players-count').value === '9'")
    assert page.is_checked("#input-audience-teens")
    assert page.is_checked("#input-difficulty-expert")
    assert page.is_checked("#input-theme-tone-spooky")
    assert page.is_checked("#input-visuals-style-noir")
    assert page.input_value("#input-theme-idea") == "Ghost in the lighthouse"
    assert page.inner_text("#field-players-names .chips").split() == ["Leo", "Mia"]
    assert "saved.mystery-config.json" in page.inner_text("#status-message")
    assert page.inner_text("#load-errors") == ""


def test_an_invalid_config_file_shows_an_error_and_changes_nothing(opened: OpenedPage) -> None:
    page: Page = opened.page
    bad_config: bytes = json.dumps({"schema_version": 1, "players": {"count": 40}}).encode()
    page.set_input_files(
        "#config-file-input",
        files=[json_file("broken.json", bad_config)],
    )
    page.wait_for_selector("#load-errors li")
    errors_text: str = page.inner_text("#load-errors")
    assert "broken.json" in errors_text
    assert "Number of players: the value must be 12 or less." in errors_text
    assert page.input_value("#input-players-count") == "4"


def test_the_prompt_is_in_a_text_box_after_copy(opened: OpenedPage) -> None:
    page: Page = opened.page
    if opened.browser_name == "chromium":
        page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.fill("#input-theme-idea", "Cake heist")
    page.click("#prompt-panel > summary")
    page.click("#copy-prompt")
    page.wait_for_selector("#status-message .icon")
    prompt: str = page.input_value("#prompt-text")
    assert page.is_visible("#prompt-text")
    assert "create-game" in prompt
    assert "mystery-forge-cake-heist.mystery-config.json" in prompt
    config_json: str = prompt.split("```json\n")[1].split("\n```")[0]
    assert normalize_config(json.loads(config_json)).findings == []
    if opened.browser_name == "chromium":
        # The Windows clipboard stores CRLF line ends.
        clipboard_text: str = page.evaluate("navigator.clipboard.readText()")
        assert clipboard_text.replace("\r\n", "\n") == prompt


def test_the_draft_survives_a_reload(opened: OpenedPage) -> None:
    page: Page = opened.page
    page.check("#input-difficulty-hard")
    page.wait_for_function("localStorage.length > 0")
    page.reload()
    page.wait_for_selector("#section-players")
    assert page.is_checked("#input-difficulty-hard")
    page.click("#reset-config")
    assert page.is_checked("#input-difficulty-medium")
    page.click("#status-message .status__action")
    assert page.is_checked("#input-difficulty-hard")


def test_the_page_works_when_storage_throws(browser: Browser) -> None:
    blocked: OpenedPage = open_page(browser, init_script=THROWING_STORAGE_SCRIPT)
    try:
        page: Page = blocked.page
        page.check("#input-difficulty-hard")
        page.wait_for_timeout(500)
        downloaded: dict[str, Any] = download_config(page)
        assert downloaded["difficulty"] == "hard"
        assert blocked.errors == []
    finally:
        blocked.page.context.close()
