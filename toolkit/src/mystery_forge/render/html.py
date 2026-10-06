"""Build the self-contained HTML of one output from its sheet plan: the Jinja environment and the page skeleton.

The environment uses `StrictUndefined`, so a template that reads a missing value fails the render instead of
printing an empty field. Autoescape is on: only HTML that the assembler or a mechanic built goes in as `Markup`.
"""

from functools import cache

from jinja2 import Environment, PackageLoader, StrictUndefined
from markupsafe import Markup

from mystery_forge.i18n import text
from mystery_forge.render.document_body import speaker_lines
from mystery_forge.render.fonts import font_face_css
from mystery_forge.render.sheets import OutputId, OutputPlan
from mystery_forge.render.themes import StyleSettings, theme_css

OUTPUT_TITLE_KEYS: dict[OutputId, str] = {
    "manual": "manual_title",
    "materials": "materials_title",
    "hints": "hints_title",
    "solutions": "solutions_title",
}


@cache
def template_environment() -> Environment:
    environment = Environment(
        loader=PackageLoader("mystery_forge.render", "templates"),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.globals["speaker_lines"] = speaker_lines
    return environment


class Translator:
    """The `t()` of the templates: a fixed text of the game language, with every value turned into text."""

    def __init__(self, language: str) -> None:
        self.language: str = language

    def __call__(self, key: str, **values: object) -> str:
        return text(self.language, key, **{name: str(value) for name, value in values.items()})


def render_output_html(plan: OutputPlan, settings: StyleSettings, title: str, language: str) -> str:
    """Return the HTML of one output, with its fonts and its CSS inline."""
    translate = Translator(language)
    css: str = font_face_css(settings.font_families) + "\n" + theme_css(settings)
    return (
        template_environment()
        .get_template("output.html.j2")
        .render(
            plan=plan,
            settings=settings,
            language=language,
            title=f"{title} · {translate(OUTPUT_TITLE_KEYS[plan.id])}",
            # The CSS comes from the package files and the bundled fonts, never from game content.
            css=Markup(css),
            t=translate,
        )
    )
