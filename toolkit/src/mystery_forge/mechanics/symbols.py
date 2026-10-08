"""Symbol mechanics: each letter of the message becomes an inline SVG glyph.

Every message glyph is `<svg class="mf-glyph" data-symbol="A">`; the decoder reads the `data-symbol` attributes back.
A key glyph carries `data-key-symbol` instead, so the decoder never reads the key. The SVG draws with `currentColor`
only, so a grayscale or low-ink print keeps every glyph readable.
"""

import random
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mystery_forge.answers import normalize_answer
from mystery_forge.mechanics.base import (
    Artifact,
    ArtifactPart,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
)
from mystery_forge.mechanics.scripts import is_latin, require_standalone_letters
from mystery_forge.mechanics.text_tools import attribute_values, plaintext_for, require_no_digits

ALPHABET: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# The longest run of glyphs with no gap: a message in a language without spaces still wraps on the page.
MAX_GLYPH_RUN: int = 8
PLAINTEXT_DESCRIPTION: str = (
    "The message to encode. It must contain the answer. Leave it empty to encode the answer alone. "
    "Letters only: spell numbers as words. Punctuation is dropped."
)
KEY_PARTS_DESCRIPTION: str = (
    "Split the key over this many parts (1 to 4), each printed in another document with {{artifact:<puzzle id>.key1}}, "
    "{{artifact:<puzzle id>.key2}}, and so on. Each part holds a run of the alphabet. 0 prints no separate key."
)
STROKE_ATTRIBUTES: str = (
    'fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"'
)


@dataclass(frozen=True)
class Glyph:
    """One letter as SVG: its inner elements, its view box, and how a text-only solver perceives it."""

    body: str
    view_box: str
    description: str


def glyph_svg(letter: str, glyph: Glyph, attribute: str) -> str:
    return (
        f'<svg class="mf-glyph" {attribute}="{letter}" viewBox="{glyph.view_box}">'
        f"<g {STROKE_ATTRIBUTES}>{glyph.body}</g></svg>"
    )


def dot(x: float, y: float) -> str:
    return f'<circle cx="{x}" cy="{y}" r="3" fill="currentColor" stroke="none"/>'


def message_html(
    mechanic_id: str, plaintext: str, glyphs: Mapping[str, Glyph], include_key: bool, alphabet: str = ALPHABET
) -> str:
    words: list[str] = [
        '<span class="mf-glyph-word">'
        + "".join(glyph_svg(letter, glyphs[letter], "data-symbol") for letter in word)
        + "</span>"
        for word in plaintext.split(" ")
    ]
    gap: str = '<span class="mf-glyph-gap" data-symbol=" "></span>'
    message: str = f'<div class="mf-glyph-message">{gap.join(words)}</div>'
    key_html: str = key_chart_html(glyphs, alphabet) if include_key else ""
    return f'<div class="mf-symbols mf-{mechanic_id}">{message}{key_html}</div>'


def key_chart_html(glyphs: Mapping[str, Glyph], letters: str = ALPHABET) -> str:
    entries: str = "".join(
        f'<span class="mf-glyph-key-entry">{glyph_svg(letter, glyphs[letter], "data-key-symbol")}'
        f'<span class="mf-glyph-key-letter">{letter}</span></span>'
        for letter in letters
    )
    return f'<div class="mf-glyph-key">{entries}</div>'


def key_solver_text(glyphs: Mapping[str, Glyph], letters: str = ALPHABET) -> str:
    return "Key: " + ", ".join(f"{letter} = {glyphs[letter].description}" for letter in letters)


def message_solver_text(
    label: str, plaintext: str, glyphs: Mapping[str, Glyph], include_key: bool, alphabet: str = ALPHABET
) -> str:
    words: list[str] = [" ".join(glyphs[letter].description for letter in word) for word in plaintext.split(" ")]
    text: str = f"{label}: {' / '.join(words)}"
    if not include_key:
        return text
    return text + "\n" + key_solver_text(glyphs, alphabet)


def key_parts(
    mechanic_id: str, glyphs: Mapping[str, Glyph], count: int, include_key: bool, alphabet: str = ALPHABET
) -> tuple[ArtifactPart, ...]:
    """Split the key into `count` runs of the alphabet, for other documents to print: a key on another prop makes
    the players connect two documents, while a key next to the message turns the puzzle into a worksheet."""
    if count and include_key:
        raise MechanicBuildError(
            "The key cannot go both next to the message and in separate parts.",
            fix_hint="Set include_key to false when you use key_parts.",
        )
    size: int = -(-len(alphabet) // count) if count else 0
    runs: list[str] = [alphabet[start : start + size] for start in range(0, len(alphabet), size)] if count else []
    return tuple(
        ArtifactPart(
            name=f"key{number}",
            html=f'<div class="mf-symbols mf-{mechanic_id}">{key_chart_html(glyphs, letters)}</div>',
            solver_text=key_solver_text(glyphs, letters),
        )
        for number, letters in enumerate(runs, start=1)
    )


def symbol_plaintext(raw_plaintext: str | None, context: MechanicContext, mechanic_name: str) -> str:
    plaintext: str = plaintext_for(raw_plaintext, context, keep_punctuation=False)
    require_no_digits(plaintext, mechanic_name)
    return plaintext


def decode_symbols(rendered: RenderedArtifact, params: BaseModel, context: MechanicContext) -> str:
    return "".join(attribute_values(rendered.html, "data-symbol"))


# pigpen-cipher

BOX_SIDES: dict[str, str] = {
    "top": '<line x1="6" y1="6" x2="34" y2="6"/>',
    "bottom": '<line x1="6" y1="34" x2="34" y2="34"/>',
    "left": '<line x1="6" y1="6" x2="6" y2="34"/>',
    "right": '<line x1="34" y1="6" x2="34" y2="34"/>',
}
# The four parts of the pigpen X, in letter order (S, T, U, V): the V shape, its opening, and where its dot goes.
X_PARTS: list[tuple[str, str, tuple[int, int]]] = [
    ("6,8 20,32 34,8", "up", (20, 16)),
    ("8,6 32,20 8,34", "left", (16, 20)),
    ("32,6 8,20 32,34", "right", (24, 20)),
    ("6,32 20,8 34,32", "down", (20, 24)),
]


def pigpen_box(position: int, with_dot: bool) -> Glyph:
    row: int = position // 3
    column: int = position % 3
    sides: list[str] = [
        side
        for side, present in (("top", row > 0), ("bottom", row < 2), ("left", column > 0), ("right", column < 2))
        if present
    ]
    body: str = "".join(BOX_SIDES[side] for side in sides) + (dot(20, 20) if with_dot else "")
    return Glyph(body, "0 0 40 40", f"[box: {' '.join(sides)}{', dot' if with_dot else ''}]")


def pigpen_x(part: int, with_dot: bool) -> Glyph:
    points, opening, (dot_x, dot_y) = X_PARTS[part]
    body: str = f'<polyline points="{points}"/>' + (dot(dot_x, dot_y) if with_dot else "")
    return Glyph(body, "0 0 40 40", f"[V: opening {opening}{', dot' if with_dot else ''}]")


PIGPEN_GLYPHS: dict[str, Glyph] = {
    **{ALPHABET[position]: pigpen_box(position, with_dot=False) for position in range(9)},
    **{ALPHABET[9 + position]: pigpen_box(position, with_dot=True) for position in range(9)},
    **{ALPHABET[18 + part]: pigpen_x(part, with_dot=False) for part in range(4)},
    **{ALPHABET[22 + part]: pigpen_x(part, with_dot=True) for part in range(4)},
}


class PigpenParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(default=None, description=PLAINTEXT_DESCRIPTION)
    include_key: bool = Field(
        default=False, description="Print the pigpen key (every letter with its symbol) next to the message."
    )
    key_parts: int = Field(default=0, ge=0, le=4, description=KEY_PARTS_DESCRIPTION)


def build_pigpen(params: PigpenParams, context: MechanicContext) -> Artifact:
    plaintext: str = symbol_plaintext(params.plaintext, context, "the pigpen cipher")
    return Artifact(
        html=message_html("pigpen-cipher", plaintext, PIGPEN_GLYPHS, params.include_key),
        solver_text=message_solver_text("Symbols", plaintext, PIGPEN_GLYPHS, params.include_key),
        parts=key_parts("pigpen-cipher", PIGPEN_GLYPHS, params.key_parts, params.include_key),
    )


# braille

BRAILLE_DOTS: dict[str, str] = {
    "A": "1", "B": "12", "C": "14", "D": "145", "E": "15", "F": "124", "G": "1245", "H": "125", "I": "24",
    "J": "245", "K": "13", "L": "123", "M": "134", "N": "1345", "O": "135", "P": "1234", "Q": "12345",
    "R": "1235", "S": "234", "T": "2345", "U": "136", "V": "1236", "W": "2456", "X": "1346", "Y": "13456",
    "Z": "1356",
}  # fmt: skip
# Dots 1-2-3 run down the left column and dots 4-5-6 down the right column.
BRAILLE_DOT_CENTERS: dict[str, tuple[int, int]] = {
    "1": (9, 10), "2": (9, 22), "3": (9, 34), "4": (21, 10), "5": (21, 22), "6": (21, 34),
}  # fmt: skip


def braille_cell(dots: str) -> Glyph:
    # The outlined empty dots show the shape of the cell, so the players can tell dot 1 from dot 4.
    body: str = "".join(
        dot(x, y) if number in dots else f'<circle cx="{x}" cy="{y}" r="3" stroke-width="1"/>'
        for number, (x, y) in BRAILLE_DOT_CENTERS.items()
    )
    return Glyph(body, "0 0 30 44", f"[dots {'-'.join(dots)}]")


BRAILLE_GLYPHS: dict[str, Glyph] = {letter: braille_cell(dots) for letter, dots in BRAILLE_DOTS.items()}


class BrailleParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(default=None, description=PLAINTEXT_DESCRIPTION)
    include_key: bool = Field(
        default=False, description="Print the Braille key (every letter with its cell) next to the message."
    )
    key_parts: int = Field(default=0, ge=0, le=4, description=KEY_PARTS_DESCRIPTION)


def build_braille(params: BrailleParams, context: MechanicContext) -> Artifact:
    plaintext: str = symbol_plaintext(params.plaintext, context, "Braille")
    return Artifact(
        html=message_html("braille", plaintext, BRAILLE_GLYPHS, params.include_key),
        solver_text=message_solver_text("Symbols", plaintext, BRAILLE_GLYPHS, params.include_key),
        parts=key_parts("braille", BRAILLE_GLYPHS, params.key_parts, params.include_key),
    )


# symbol-substitution

SHAPES: list[str] = [
    '<circle cx="20" cy="20" r="11"/>',
    '<polygon points="20,9 31,30 9,30"/>',
    '<polygon points="9,10 31,10 20,31"/>',
    '<rect x="10" y="10" width="20" height="20"/>',
    '<polygon points="20,8 32,20 20,32 8,20"/>',
    '<polyline points="9,28 20,12 31,28"/>',
    '<line x1="15" y1="9" x2="15" y2="31"/><line x1="25" y1="9" x2="25" y2="31"/>',
    '<path d="M9 11 A11 11 0 0 0 31 11"/>',
]
MARKS: list[str] = [
    "",
    dot(20, 18),
    '<line x1="10" y1="37" x2="30" y2="37"/>',
    '<line x1="10" y1="3" x2="30" y2="3"/>',
]
# Every shape with every mark: 32 distinct glyphs, of which each game uses 26.
SYMBOL_POOL: list[Glyph] = [
    Glyph(shape + mark, "0 0 40 40", f"[glyph {number}]")
    for number, (shape, mark) in enumerate(((shape, mark) for mark in MARKS for shape in SHAPES), start=1)
]


def substitution_glyphs(seed: int, alphabet: str = ALPHABET) -> dict[str, Glyph]:
    chosen: list[Glyph] = random.Random(seed).sample(SYMBOL_POOL, len(alphabet))
    return dict(zip(alphabet, chosen, strict=True))


def native_plaintext(raw_plaintext: str | None, context: MechanicContext) -> str:
    """The message in its own script (kana, Cyrillic, Greek): letters only, upper case where it exists.

    A word longer than `MAX_GLYPH_RUN` letters is split, so that a language without spaces still wraps on the page.
    """
    text: str = unicodedata.normalize("NFC", context.answer if raw_plaintext is None else raw_plaintext).upper()
    require_standalone_letters(text, "a symbol key")
    words: list[str] = ["".join(character for character in word if character.isalpha()) for word in text.split()]
    plaintext: str = " ".join(
        word[start : start + MAX_GLYPH_RUN] for word in words for start in range(0, len(word), MAX_GLYPH_RUN)
    )
    if context.normalized_answer not in normalize_answer(plaintext, context.language):
        raise MechanicBuildError(
            f"The plaintext '{plaintext}' does not contain the answer '{context.answer}'.",
            fix_hint="Write a plaintext that includes the answer word in letters, with no digits.",
        )
    return plaintext


class SymbolSubstitutionParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(default=None, description=PLAINTEXT_DESCRIPTION)
    include_key: bool = Field(
        default=True,
        description="Print the key (every letter with its symbol) next to the message: a worksheet, fine for kids. "
        "For a real puzzle, set it to false and use key_parts.",
    )
    key_parts: int = Field(default=0, ge=0, le=4, description=KEY_PARTS_DESCRIPTION)


def build_symbol_substitution(params: SymbolSubstitutionParams, context: MechanicContext) -> Artifact:
    # Outside A to Z, the key holds the letters of the message: kana or kanji are too many for one key.
    latin: bool = is_latin(context.normalized_answer)
    plaintext: str = (
        symbol_plaintext(params.plaintext, context, "the symbol alphabet")
        if latin
        else native_plaintext(params.plaintext, context)
    )
    alphabet: str = ALPHABET if latin else "".join(sorted(set(plaintext) - {" "}))
    if len(alphabet) > len(SYMBOL_POOL):
        raise MechanicBuildError(
            f"The message has {len(alphabet)} different letters, but the symbol key holds at most {len(SYMBOL_POOL)}.",
            fix_hint="Write a shorter message, or one that repeats its letters more.",
        )
    glyphs: dict[str, Glyph] = substitution_glyphs(context.seed, alphabet)
    # The symbols are new for every game, so only the builder can draw the key: without it, nobody can solve this.
    if not params.include_key and not params.key_parts:
        raise MechanicBuildError(
            "The symbols are new for this game, but the material prints no key.",
            fix_hint="Set key_parts to 1 to 4 and print each part in another document, or set include_key to true.",
        )
    return Artifact(
        html=message_html("symbol-substitution", plaintext, glyphs, params.include_key, alphabet),
        solver_text=message_solver_text("Symbols", plaintext, glyphs, params.include_key, alphabet),
        parts=key_parts("symbol-substitution", glyphs, params.key_parts, params.include_key, alphabet),
    )


IMPLEMENTATIONS: tuple[MechanicImplementation[Any], ...] = (
    MechanicImplementation(
        id="pigpen-cipher", params_model=PigpenParams, build=build_pigpen, decode_rendered=decode_symbols
    ),
    MechanicImplementation(
        id="braille", params_model=BrailleParams, build=build_braille, decode_rendered=decode_symbols
    ),
    MechanicImplementation(
        id="symbol-substitution",
        params_model=SymbolSubstitutionParams,
        build=build_symbol_substitution,
        decode_rendered=decode_symbols,
    ),
)
