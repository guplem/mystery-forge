"""Wordplay verifiers: the agent writes the material in a document, and the code checks the stated rule.

A verifier reads the plain text of a document from `context.documents`. It raises `MechanicBuildError` with the
letters that it found when the rule does not spell the answer.
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
)
from mystery_forge.mechanics.text_tools import escape_text, fold_text, letters_only, marked_texts

DOCUMENT_DESCRIPTION: str = "The id of the document that holds the hidden message."
EXACT_DESCRIPTION: str = (
    "True: the extracted letters must be the answer and nothing else. False: they must contain the answer."
)
UNIT_SPLITTERS: dict[str, re.Pattern[str]] = {
    "lines": re.compile(r"\n"),
    "sentences": re.compile(r"(?<=[.!?])\s+"),
    "paragraphs": re.compile(r"\n\s*\n"),
}


def document_text(document_id: str, context: MechanicContext) -> str:
    if document_id not in context.documents:
        raise MechanicBuildError(
            f"The document '{document_id}' does not exist.",
            fix_hint=f"Use one of these document ids: {', '.join(sorted(context.documents))}.",
        )
    return context.documents[document_id]


def require_spelled_answer(extracted: str, exact: bool, what: str, context: MechanicContext) -> None:
    """Raise a build error when the extracted letters do not spell (or, when not exact, contain) the answer."""
    if exact and extracted.lower() != context.normalized_answer:
        raise MechanicBuildError(
            f"The {what} spell '{extracted}', not the answer '{context.answer}'.",
            fix_hint="Rewrite the document so that the letters spell the answer, "
            "or set exact to false when other letters may come before or after it.",
        )
    if context.normalized_answer not in extracted.lower():
        raise MechanicBuildError(
            f"The {what} spell '{extracted}', which does not contain the answer '{context.answer}'.",
            fix_hint="Rewrite the document so that the letters include the answer.",
        )


class AcrosticParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: str = Field(description=DOCUMENT_DESCRIPTION)
    mode: Literal["lines", "sentences", "paragraphs"] = Field(
        default="lines", description="Which units give one letter each: lines, sentences, or paragraphs."
    )
    letter: Literal["first", "last"] = Field(
        default="first", description="Which letter of each unit counts: the first or the last."
    )
    exact: bool = Field(default=True, description=EXACT_DESCRIPTION)


def build_acrostic(params: AcrosticParams, context: MechanicContext) -> Artifact:
    units: list[str] = UNIT_SPLITTERS[params.mode].split(document_text(params.document, context))
    unit_letters: list[str] = [letters for letters in (letters_only(unit) for unit in units) if letters]
    extracted: str = "".join(letters[0] if params.letter == "first" else letters[-1] for letters in unit_letters)
    require_spelled_answer(extracted, params.exact, f"{params.letter} letters of the {params.mode}", context)
    return Artifact(html="", solver_text="")


class AnagramParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    letters: str = Field(
        description="The letters of the answer in a scrambled order, such as 'LLIM' for MILL. "
        "Spaces and accents do not count. Leave out a leading article that the answer normalization drops."
    )


def anagram_tiles(letters: str) -> str:
    return fold_text(letters, keep_punctuation=False).replace(" ", "")


def build_anagram(params: AnagramParams, context: MechanicContext) -> Artifact:
    tiles: str = anagram_tiles(params.letters)
    if sorted(tiles.lower()) != sorted(context.normalized_answer):
        raise MechanicBuildError(
            f"The letters '{tiles}' do not use exactly the letters of the answer '{context.answer}'.",
            fix_hint="Use each letter of the answer exactly once, in a scrambled order.",
        )
    if tiles.lower() == context.normalized_answer:
        raise MechanicBuildError(
            f"The letters '{tiles}' spell the answer in order, so they are not scrambled.",
            fix_hint="Shuffle the letters so that the answer does not show.",
        )
    spans: str = "".join(f'<span class="mf-tile">{escape_text(tile)}</span>' for tile in tiles)
    return Artifact(html=f'<div class="mf-anagram">{spans}</div>', solver_text=f"Letter tiles: {' '.join(tiles)}")


def decode_anagram(rendered: RenderedArtifact, params: AnagramParams, context: MechanicContext) -> str:
    """Return the answer when the rendered tiles hold exactly its letters, else the tiles as they are."""
    tiles: str = "".join(marked_texts(rendered.html, "mf-tile"))
    return context.normalized_answer if sorted(tiles.lower()) == sorted(context.normalized_answer) else tiles


class HiddenEveryNthParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: str = Field(description=DOCUMENT_DESCRIPTION)
    n: int = Field(default=2, ge=1, description="Take every n-th unit: 2 takes every second letter or word.")
    start: int = Field(default=1, ge=1, description="The position (from 1) of the first unit to take.")
    unit: Literal["letter", "word"] = Field(
        default="letter",
        description="'letter': count the letters of the document. 'word': count the words and take the first "
        "letter of each word that you pick.",
    )
    exact: bool = Field(default=True, description=EXACT_DESCRIPTION)


def build_hidden_every_nth(params: HiddenEveryNthParams, context: MechanicContext) -> Artifact:
    text: str = document_text(params.document, context)
    if params.unit == "letter":
        units: list[str] = list(letters_only(text))
    else:
        units = [letters for letters in (letters_only(word) for word in text.split()) if letters]
    extracted: str = "".join(unit[0] for unit in units[params.start - 1 :: params.n])
    what: str = f"letters found with n={params.n}, start={params.start}, unit={params.unit}"
    require_spelled_answer(extracted, params.exact, what, context)
    return Artifact(html="", solver_text="")


IMPLEMENTATIONS: tuple[MechanicImplementation[Any], ...] = (
    MechanicImplementation(id="acrostic", params_model=AcrosticParams, build=build_acrostic),
    MechanicImplementation(
        id="anagram", params_model=AnagramParams, build=build_anagram, decode_rendered=decode_anagram
    ),
    MechanicImplementation(id="hidden-every-nth", params_model=HiddenEveryNthParams, build=build_hidden_every_nth),
)
