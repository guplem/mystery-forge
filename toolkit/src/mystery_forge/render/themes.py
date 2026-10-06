"""Themes (the config's visual styles) and the color modes, as the settings and the CSS of one render.

A theme is a set of fonts (one per role) plus a CSS file of custom properties (`themes/<id>.css`).
`themes/base.css` holds the layout of every sheet and document kind, and it reads only those properties.
The color modes change the same properties: grayscale for a black-and-white printer, low-ink for ink saving.
"""

from dataclasses import dataclass
from typing import Final, Literal

from mystery_forge.config import Paper
from mystery_forge.game import Game
from mystery_forge.render.package_files import read_package_text
from mystery_forge.spec.models import VisualStyle

FontRole = Literal["heading", "body", "hand", "type", "mono", "stamp", "display"]
FONT_ROLES: Final[tuple[FontRole, ...]] = ("heading", "body", "hand", "type", "mono", "stamp", "display")
READABLE_FONT: Final[str] = "Atkinson Hyperlegible"
DEFAULT_THEME: Final[VisualStyle] = "vintage"

# Width and height of one sheet. `@page` uses the same values, so one sheet is one printed page.
PAPER_SIZES: Final[dict[Paper, tuple[str, str]]] = {"A4": ("210mm", "297mm"), "Letter": ("215.9mm", "279.4mm")}

GENERIC_FAMILIES: Final[dict[str, str]] = {
    "Special Elite": "monospace",
    "Courier Prime": "monospace",
    "Share Tech Mono": "monospace",
    "Caveat": "cursive",
    "Bebas Neue": "sans-serif",
    "Oswald": "sans-serif",
    "Source Sans 3": "sans-serif",
    "Orbitron": "sans-serif",
    "Fredoka": "sans-serif",
    "Atkinson Hyperlegible": "sans-serif",
}


@dataclass(frozen=True)
class Theme:
    id: VisualStyle
    fonts: dict[FontRole, str]


def theme(
    theme_id: VisualStyle, heading: str, body: str, hand: str, typewriter: str, mono: str, stamp: str, display: str
) -> Theme:
    return Theme(
        id=theme_id,
        fonts={
            "heading": heading,
            "body": body,
            "hand": hand,
            "type": typewriter,
            "mono": mono,
            "stamp": stamp,
            "display": display,
        },
    )


THEMES: Final[dict[str, Theme]] = {
    item.id: item
    for item in (
        theme(
            "vintage", "Playfair Display", "Libre Baskerville", "Caveat", "Special Elite", "Courier Prime",
            "Bebas Neue", "Playfair Display",
        ),
        theme(
            "noir", "Bebas Neue", "Old Standard TT", "Caveat", "Special Elite", "Courier Prime",
            "Bebas Neue", "Bebas Neue",
        ),
        theme(
            "modern", "Oswald", "Source Sans 3", "Caveat", "Courier Prime", "Share Tech Mono", "Oswald", "Oswald",
        ),
        theme(
            "victorian", "IM Fell English", "EB Garamond", "Caveat", "Special Elite", "Courier Prime",
            "Cinzel", "Cinzel",
        ),
        theme(
            "scifi", "Orbitron", "Source Sans 3", "Caveat", "Share Tech Mono", "Share Tech Mono", "Orbitron",
            "Orbitron",
        ),
        theme(
            "fantasy", "Cinzel", "EB Garamond", "Caveat", "IM Fell English", "Courier Prime", "Cinzel", "Cinzel",
        ),
        theme("kids", "Fredoka", "Fredoka", "Caveat", "Courier Prime", "Courier Prime", "Fredoka", "Fredoka"),
        theme(
            "minimal", "Source Sans 3", "Source Sans 3", "Caveat", "Courier Prime", "Courier Prime", "Oswald",
            "Source Sans 3",
        ),
    )
}  # fmt: skip


@dataclass(frozen=True)
class StyleSettings:
    theme: Theme
    paper: Paper
    grayscale: bool
    low_ink: bool
    readable_font: bool

    def font_for(self, role: FontRole) -> str:
        return READABLE_FONT if role == "body" and self.readable_font else self.theme.fonts[role]

    @property
    def font_families(self) -> frozenset[str]:
        return frozenset(self.font_for(role) for role in FONT_ROLES)

    @property
    def body_classes(self) -> str:
        classes: list[str] = [f"theme-{self.theme.id}", f"paper-{self.paper.lower()}"]
        if self.grayscale:
            classes.append("mode-grayscale")
        if self.low_ink:
            classes.append("mode-low-ink")
        if self.readable_font:
            classes.append("readable-font")
        return " ".join(classes)


def style_settings(game: Game, theme_override: VisualStyle | None) -> StyleSettings:
    """Pick the theme (the override, the config style, the story style, then vintage) and the color modes."""
    return StyleSettings(
        theme=THEMES[chosen_theme_id(game, theme_override)],
        paper=game.config.equipment.paper,
        grayscale=game.config.equipment.printer == "black_and_white",
        low_ink=game.config.equipment.ink_saving,
        readable_font=game.config.visuals.readable_font,
    )


def chosen_theme_id(game: Game, theme_override: VisualStyle | None) -> VisualStyle:
    if theme_override is not None:
        return theme_override
    configured_style = game.config.visuals.style
    if configured_style == "auto":
        return game.story.visual_style or DEFAULT_THEME
    return configured_style


def font_stack(family: str) -> str:
    return f'"{family}",{GENERIC_FAMILIES.get(family, "serif")}'


def theme_css(settings: StyleSettings) -> str:
    """Return the CSS of one render: the page size, the font roles, the base layout, and the theme properties."""
    width, height = PAPER_SIZES[settings.paper]
    font_variables: str = ";".join(f"--font-{role}:{font_stack(settings.font_for(role))}" for role in FONT_ROLES)
    page: str = f"@page{{size:{width} {height};margin:0}}"
    root: str = f":root{{--sheet-width:{width};--sheet-height:{height};{font_variables}}}"
    return "\n".join(
        (page, root, read_package_text("themes/base.css"), read_package_text(f"themes/{settings.theme.id}.css"))
    )
