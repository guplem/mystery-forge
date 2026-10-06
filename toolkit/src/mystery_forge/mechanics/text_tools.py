"""Text helpers that the mechanic builders share: letter folding, plaintext checks, escaping, and DOM reading.

Builders fold text to the letters A-Z, the digits, and single word spaces, with the same accent and special-letter
rules as `normalize_answer`. Unlike `normalize_answer`, the folding keeps the word spaces, because a cipher message
shows its word breaks.
"""

import random
import unicodedata
from html.parser import HTMLParser

from markupsafe import escape

from mystery_forge.answers import SPECIAL_LETTERS, normalize_answer
from mystery_forge.mechanics.base import MechanicBuildError, MechanicContext

KEPT_PUNCTUATION: frozenset[str] = frozenset(".,!?'-:;")
LETTERS: frozenset[str] = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGITS: frozenset[str] = frozenset("0123456789")


def fold_text(text: str, keep_punctuation: bool) -> str:
    """Return uppercase A-Z, digits, and single spaces (plus basic punctuation when asked); drop every other sign."""
    decomposed: str = unicodedata.normalize("NFKD", text)
    without_marks: str = "".join(character for character in decomposed if not unicodedata.combining(character))
    transliterated: str = "".join(SPECIAL_LETTERS.get(character, character) for character in without_marks.casefold())
    kept: list[str] = []
    for character in transliterated.upper():
        if character in LETTERS or character in DIGITS or (keep_punctuation and character in KEPT_PUNCTUATION):
            kept.append(character)
        elif character.isspace():
            kept.append(" ")
    return " ".join("".join(kept).split())


def letters_only(text: str) -> str:
    """Return only the folded letters A-Z of the text, with no spaces."""
    return "".join(character for character in fold_text(text, keep_punctuation=False) if character in LETTERS)


def plaintext_for(raw_plaintext: str | None, context: MechanicContext, keep_punctuation: bool) -> str:
    """Return the folded message to encode: the given plaintext, or the answer. The message must contain the answer."""
    if not context.normalized_answer:
        raise MechanicBuildError(
            f"The answer '{context.answer}' has no letters or digits to encode.",
            fix_hint="Give the puzzle an answer with at least one letter or digit.",
        )
    plaintext: str = fold_text(context.answer if raw_plaintext is None else raw_plaintext, keep_punctuation)
    if context.normalized_answer not in normalize_answer(plaintext, context.language):
        raise MechanicBuildError(
            f"The plaintext '{plaintext}' does not contain the answer '{context.answer}'.",
            fix_hint="Write a plaintext that includes the answer word, or leave plaintext empty to encode the answer.",
        )
    return plaintext


def require_no_digits(plaintext: str, mechanic_name: str) -> None:
    """Raise a build error when the folded plaintext has a digit that the mechanic cannot encode."""
    if any(character in DIGITS for character in plaintext):
        raise MechanicBuildError(
            f"The plaintext '{plaintext}' has digits, which {mechanic_name} cannot encode.",
            fix_hint="Spell the numbers as words, or pick a mechanic that encodes digits.",
        )


def cyclic_permutation(count: int, rng: random.Random) -> list[int]:
    """Return a random order of `range(count)` in which no item keeps its place (Sattolo's algorithm).

    A scramble or a substitution alphabet must never leave an item in place: a letter that maps to itself gives part
    of the solution away.
    """
    order: list[int] = list(range(count))
    for index in range(count - 1, 0, -1):
        other: int = rng.randrange(index)
        order[index], order[other] = order[other], order[index]
    return order


def escape_text(text: str) -> str:
    """Return the text with every HTML special character escaped."""
    return str(escape(text))


class MarkedTextParser(HTMLParser):
    """Collects the text of each element whose class list has one class. A marked element must hold text only."""

    def __init__(self, css_class: str) -> None:
        super().__init__(convert_charrefs=True)
        self.css_class: str = css_class
        self.texts: list[str] = []
        self.capturing: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes: list[str] = (dict(attrs).get("class") or "").split()
        if self.css_class in classes:
            self.texts.append("")
            self.capturing = True

    def handle_endtag(self, tag: str) -> None:
        self.capturing = False

    def handle_data(self, data: str) -> None:
        if self.capturing:
            self.texts[-1] += data


class AttributeParser(HTMLParser):
    """Collects the values of one attribute, in document order."""

    def __init__(self, attribute: str) -> None:
        super().__init__(convert_charrefs=True)
        self.attribute: str = attribute
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name == self.attribute and value is not None:
                self.values.append(value)


def marked_texts(html: str, css_class: str) -> list[str]:
    """Return the text of every element with the class, in document order."""
    parser: MarkedTextParser = MarkedTextParser(css_class)
    parser.feed(html)
    parser.close()
    return parser.texts


def attribute_values(html: str, attribute: str) -> list[str]:
    """Return the value of the attribute on every element that has it, in document order."""
    parser: AttributeParser = AttributeParser(attribute)
    parser.feed(html)
    parser.close()
    return parser.values
