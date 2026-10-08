"""The script of a text, for the mechanics that also build outside the letters A to Z.

A maze or a symbol key in a Japanese or Russian game must use the letters of that script: a decoy in another script
would stand out at once. A script whose letters carry combining marks (Devanagari, Thai) cannot put one code point in
one cell or under one symbol, so those mechanics refuse it.
"""

import unicodedata

from mystery_forge.mechanics.base import MechanicBuildError


def script_name(character: str) -> str:
    """The first word of the Unicode name: LATIN, CYRILLIC, HIRAGANA, CJK, HANGUL, ARABIC, and so on."""
    return unicodedata.name(character, "").split(" ")[0].split("-")[0]


def letter_scripts(text: str) -> set[str]:
    return {script_name(character) for character in text if character.isalpha()}


def is_latin(text: str) -> bool:
    return letter_scripts(text) <= {"LATIN"}


def require_standalone_letters(text: str, mechanic_name: str) -> None:
    """Refuse a text whose letters combine with marks: one mark alone in a cell or under a symbol cannot be read."""
    if any(unicodedata.category(character).startswith("M") for character in unicodedata.normalize("NFC", text)):
        raise MechanicBuildError(
            f"The text '{text}' has letters that combine with marks, which {mechanic_name} cannot split.",
            fix_hint="Pick a mechanic that keeps whole words, such as a riddle, a deduction, or a timeline.",
        )


def same_script_letters(answer: str, texts: list[str]) -> str:
    """Every letter of the answer's scripts that the answer or the texts hold, sorted, in upper case where it exists."""
    scripts: set[str] = letter_scripts(answer)
    letters: set[str] = {
        character
        for text in (answer, *texts)
        for character in unicodedata.normalize("NFC", text).upper()
        if character.isalpha() and script_name(character) in scripts
    }
    return "".join(sorted(letters))
