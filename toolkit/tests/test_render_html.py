import re

import pytest
from jinja2 import UndefinedError
from test_render_support import configured, golden_game, showcase_game

from mystery_forge.game import Game
from mystery_forge.render.game_renderer import output_plans
from mystery_forge.render.html import Translator, render_output_html, template_environment
from mystery_forge.render.kinds import document_kind_ids
from mystery_forge.render.sheets import OutputPlan
from mystery_forge.render.themes import THEMES, style_settings

COLOR_MODES: dict[str, dict[str, object]] = {
    "color": {},
    "grayscale": {"printer": "black_and_white"},
    "low-ink": {"ink_saving": True},
}


def render_all(game: Game, theme: str | None = None) -> dict[str, str]:
    settings = style_settings(game, theme)  # type: ignore[arg-type]
    return {
        plan.id: render_output_html(
            plan, settings, game.story.title, game.config.language, solo=game.config.players.count == 1
        )
        for plan in output_plans(game)
    }


def sheet_count(html: str) -> int:
    return len(re.findall(r'<section class="sheet ', html))


@pytest.mark.parametrize("theme", sorted(THEMES))
@pytest.mark.parametrize("mode", sorted(COLOR_MODES))
def test_every_theme_and_color_mode_renders_every_output(theme: str, mode: str) -> None:
    game = configured(golden_game(), equipment=COLOR_MODES[mode])
    plans: dict[str, OutputPlan] = {plan.id: plan for plan in output_plans(game)}
    for output, html in render_all(game, theme).items():
        assert html.startswith("<!doctype html>")
        assert f'class="theme-{theme}' in html
        assert sheet_count(html) == len(plans[output].sheets)
        assert "@font-face" in html and "url(data:font/woff2;base64," in html
        assert "⟦" not in html
        assert "@page{size:210mm 297mm;margin:0}" in html
    if mode != "color":
        assert f"mode-{mode}" in render_all(game, theme)["manual"]


def test_the_html_title_names_the_game_and_the_output() -> None:
    html = render_all(golden_game())
    assert "<title>The Lens of Gull Rock · Game materials</title>" in html["materials"]
    assert '<html lang="en">' in html["manual"]


def test_every_document_kind_draws_its_own_paper() -> None:
    materials = render_all(showcase_game())["materials"]
    for kind in document_kind_ids():
        assert f"kind-{kind}" in materials, kind
    assert '<div class="bubble bubble-own"><span class="bubble-name">Tom</span>' in materials
    assert '<span class="speaker">HALE</span>' in materials
    assert '<figure class="mf-figure" data-image="lamp"><div class="mf-figure-art"><svg' in materials
    assert 'data-artifact="P1"' in materials
    assert "Page 1 of 2" in materials
    assert "Copy 2 of 2" in materials
    assert "Cut along the dashed line." in materials
    assert '<div class="fold-guide" aria-hidden="true"></div>' in materials


def test_game_text_is_escaped() -> None:
    game = golden_game()
    game = game.model_copy(update={"story": game.story.model_copy(update={"title": "<b>Bold</b> & co"})})
    html = render_all(game)["materials"]
    assert "&lt;b&gt;Bold&lt;/b&gt; &amp; co" in html
    assert "<b>Bold</b>" not in html


def test_a_missing_template_value_fails_the_render() -> None:
    template = template_environment().from_string("{{ nothing.here }}")
    with pytest.raises(UndefinedError):
        template.render()


def test_the_translator_turns_values_into_text() -> None:
    assert Translator("es")("cover_players", count=3) == "3 jugadores"


def test_a_spanish_game_prints_spanish_labels() -> None:
    html = render_all(configured(golden_game(), {"language": "es"}))
    assert "ALTO" in html["materials"]
    assert "Registro de respuestas" in html["materials"]
    assert "Aviso de spoilers" in html["hints"]


def test_a_solo_game_prints_one_player_and_no_group_wording() -> None:
    assert Translator("en", solo=True)("cover_players", count=1) == "1 player"
    html = render_all(configured(golden_game(), players={"count": 1}))
    assert "Answer every question. Tick" in html["materials"]
    assert "together" not in html["materials"]
