import pytest
from test_render_support import configured, golden_game, with_story

from mystery_forge.render.fonts import bundled_font_families
from mystery_forge.render.themes import (
    PAPER_SIZES,
    READABLE_FONT,
    THEMES,
    style_settings,
    theme_css,
)


def test_every_theme_uses_only_bundled_fonts_and_has_a_css_file() -> None:
    assert set(THEMES) == {"vintage", "noir", "modern", "victorian", "scifi", "fantasy", "kids", "minimal"}
    families = bundled_font_families()
    for theme in THEMES.values():
        assert set(theme.fonts.values()) <= set(families), theme.id
        settings = style_settings(configured(golden_game(), visuals={"style": theme.id}), None)
        assert f".theme-{theme.id}" in theme_css(settings), theme.id


def test_the_config_style_wins_then_the_story_style_then_vintage() -> None:
    game = golden_game()
    assert style_settings(game, None).theme.id == "vintage"
    noir_story = with_story(game, visual_style="noir")
    assert style_settings(noir_story, None).theme.id == "noir"
    assert style_settings(configured(noir_story, visuals={"style": "kids"}), None).theme.id == "kids"
    assert style_settings(noir_story, "scifi").theme.id == "scifi"


def test_color_modes_follow_the_printer_and_the_ink_saving_option() -> None:
    game = golden_game()
    color = style_settings(game, None)
    assert (color.grayscale, color.low_ink) == (False, False)
    assert color.body_classes == "theme-vintage paper-a4"
    gray = style_settings(configured(game, equipment={"printer": "black_and_white"}), None)
    assert gray.grayscale and gray.body_classes == "theme-vintage paper-a4 mode-grayscale"
    low = style_settings(configured(game, equipment={"ink_saving": True, "paper": "Letter"}), None)
    assert low.low_ink and low.body_classes == "theme-vintage paper-letter mode-low-ink"


def test_the_readable_font_replaces_the_body_font() -> None:
    game = configured(golden_game(), visuals={"readable_font": True})
    settings = style_settings(game, None)
    assert settings.font_for("body") == READABLE_FONT
    assert READABLE_FONT in settings.font_families
    assert "readable-font" in settings.body_classes
    assert style_settings(golden_game(), None).font_for("body") == THEMES["vintage"].fonts["body"]


@pytest.mark.parametrize("paper", ["A4", "Letter"])
def test_theme_css_sets_the_page_size_and_the_font_variables(paper: str) -> None:
    settings = style_settings(configured(golden_game(), equipment={"paper": paper}), None)
    css: str = theme_css(settings)
    width, height = PAPER_SIZES[settings.paper]
    assert f"@page{{size:{width} {height};margin:0}}" in css
    assert f"--sheet-width:{width}" in css
    assert '--font-heading:"Playfair Display"' in css
    assert ".sheet" in css
